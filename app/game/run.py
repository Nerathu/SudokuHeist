"""Run state machine for SudokuHeist."""

from __future__ import annotations

import copy
import random
import time
from copy import deepcopy

from app.db import clear_run, get_meta, load_run, save_run, upgrade_level
from app.game.autofill import run_auto_fills
from app.game.balance import HELP_BONUS_SCORE, INTEL_DIFFICULTIES
from app.game.intel import refresh_intel, strip_digit_from_peers, valid_candidates
from app.game.boosts import BOOSTS, boost_by_id, can_afford_boost, fifty_fifty_options, spend_score
from app.game.shop import generate_shop_offers_with_meta, reroll_cost
from app.game.tricks import meta_upgrades, random_quote, trick_by_id
from app.sudoku.generator import clues_for_difficulty, generate_puzzle
from app.sudoku.scorer import AnteScoreState, apply_placement_score, score_target_for_ante
from app.sudoku.validator import is_complete

PHASE_MAP = "map"
PHASE_ANTE = "ante"
PHASE_ANTE_VICTORY = "ante_victory"
PHASE_SHOP = "shop"
PHASE_RUN_OVER = "run_over"
PHASE_RUN_WON = "run_won"

MAP_NODES = [
    {"type": "ante", "label": "Tresor 1"},
    {"type": "shop", "label": "Schwarzmarkt"},
    {"type": "ante", "label": "Tresor 2"},
    {"type": "ante", "label": "Tresor 3"},
    {"type": "shop", "label": "Hehler"},
    {"type": "ante", "label": "Tresor 4"},
    {"type": "ante", "label": "Tresor 5"},
    {"type": "shop", "label": "Letzter Deal"},
    {"type": "boss", "label": "BOSS: Haupttresor"},
]

MAX_MOVES = 80
BOSS_MAX_MOVES = 65


def _meta_bonuses() -> dict:
    meta = get_meta()
    upgrades = meta["upgrades"]
    return {
        "extra_hearts": upgrade_level(upgrades, "extra_heart"),
        "start_beute": upgrade_level(upgrades, "start_beute") * 5,
        "shop_reroll": upgrade_level(upgrades, "shop_reroll"),
        "meta_beute": meta["meta_beute"],
        "upgrades": upgrades,
    }


def _max_hearts(trick_ids: list[str], extra: int) -> int:
    hearts = 3 + extra
    if "waschbaers_tasche" in trick_ids:
        hearts += 1
    return hearts


def _difficulty_for_node(node_index: int, is_boss: bool) -> str:
    if is_boss:
        return "boss"
    if node_index <= 2:
        return "easy"
    if node_index <= 5:
        return "medium"
    return "hard"


def _intel_enabled(ante: dict) -> bool:
    return ante.get("difficulty") in INTEL_DIFFICULTIES


def _clear_cell_intel(ante: dict, row: int, col: int) -> None:
    ante.setdefault("intel", {}).pop(f"{row},{col}", None)


def _grant_target_met(ante: dict, events: list[dict]) -> None:
    ante["target_met"] = True
    ante["score"] += HELP_BONUS_SCORE
    intel = " INTEL-Wiretap aktiv." if _intel_enabled(ante) else ""
    events.append({
        "type": "target_met",
        "message": (
            f"Beute gesichert! +{HELP_BONUS_SCORE} Hilfe-Punkte — Boosts freigeschaltet.{intel}"
        ),
        "help_bonus": HELP_BONUS_SCORE,
    })


def _start_ante(state: dict) -> None:
    node = MAP_NODES[state["map_index"]]
    is_boss = node["type"] == "boss"
    difficulty = _difficulty_for_node(state["map_index"], is_boss)
    seed = state["run_seed"] + state["map_index"] * 997
    puzzle, solution = generate_puzzle(clues=clues_for_difficulty(difficulty), seed=seed)
    state["ante"] = {
        "puzzle": puzzle,
        "solution": solution,
        "player_grid": deepcopy(puzzle),
        "fixed": [[puzzle[r][c] != 0 for c in range(9)] for r in range(9)],
        "score": 0,
        "score_target": score_target_for_ante(state["antes_completed"], is_boss, state["trick_ids"]),
        "moves_left": BOSS_MAX_MOVES if is_boss else MAX_MOVES,
        "is_boss": is_boss,
        "difficulty": difficulty,
        "ante_state": {
            "combo_streak": 0,
            "first_row_done": False,
            "mistakes_forgiven_left": 1 if "waschbaer_ablenkung" in state["trick_ids"] else 0,
            "cheat_sheet_left": 0,
        },
        "target_met": False,
        "hints": {},
        "intel": {},
        "started_at": time.time(),
    }
    state["phase"] = PHASE_ANTE
    state["last_quote"] = random_quote(state["rng"])
    bootstrap_events: list[dict] = []
    run_auto_fills(state=state, events=bootstrap_events)


def new_run(seed: int | None = None) -> dict:
    clear_run()
    bonuses = _meta_bonuses()
    rng = random.Random(seed if seed is not None else int(time.time()))
    run_seed = rng.randint(1, 999_999_999)
    rng.seed(run_seed)
    state = {
        "run_seed": run_seed,
        "phase": PHASE_MAP,
        "map_index": 0,
        "map_nodes": MAP_NODES,
        "hearts": _max_hearts([], bonuses["extra_hearts"]),
        "max_hearts": _max_hearts([], bonuses["extra_hearts"]),
        "beute": 8 + bonuses["start_beute"],
        "trick_ids": [],
        "kniffs": {},
        "antes_completed": 0,
        "rng_state": _serialize_rng(rng),
        "shop": None,
        "ante": None,
        "result": None,
        "meta": bonuses,
    }
    state["rng"] = rng
    save_run(_serialize(state))
    return public_state(state)


def _serialize_rng(rng: random.Random) -> list:
    version, internal, gauss = rng.getstate()
    return [version, list(internal), gauss]


def _hydrate_rng(data: list) -> random.Random:
    rng = random.Random()
    rng.setstate((data[0], tuple(data[1]), data[2]))
    return rng


def _serialize(state: dict) -> dict:
    data = copy.deepcopy(state)
    data.pop("rng", None)
    if "rng" in state:
        data["rng_state"] = _serialize_rng(state["rng"])
    return data


def _hydrate(data: dict) -> dict:
    state = copy.deepcopy(data)
    state["rng"] = _hydrate_rng(state["rng_state"])
    return state


def get_state() -> dict | None:
    raw = load_run()
    if not raw:
        return None
    return public_state(_hydrate(raw))


def _cells_remaining(ante: dict) -> int:
    return sum(1 for r in range(9) for c in range(9) if ante["player_grid"][r][c] == 0)


def _wrong_cells(ante: dict) -> list[list[int]]:
    wrong: list[list[int]] = []
    for r in range(9):
        for c in range(9):
            val = ante["player_grid"][r][c]
            if val != 0 and val != ante["solution"][r][c]:
                wrong.append([r, c])
    return wrong


def _is_wrong_player_cell(ante: dict, row: int, col: int) -> bool:
    val = ante["player_grid"][row][col]
    return val != 0 and val != ante["solution"][row][col]


def _next_shop_label(state: dict) -> str:
    for i in range(state["map_index"] + 1, len(MAP_NODES)):
        if MAP_NODES[i]["type"] == "shop":
            return MAP_NODES[i]["label"]
    return "Schwarzmarkt"


def _ante_public(ante: dict, state: dict | None = None) -> dict:
    score = ante["score"]
    target = ante["score_target"]
    target_met = ante.get("target_met", False)
    points_to_target = max(0, target - score)
    return {
        "player_grid": ante["player_grid"],
        "fixed": ante["fixed"],
        "score": score,
        "score_target": target,
        "target_met": target_met,
        "points_to_target": points_to_target,
        "score_progress": min(1.0, score / target if target else 1.0),
        "moves_left": ante["moves_left"],
        "is_boss": ante["is_boss"],
        "difficulty": ante["difficulty"],
        "combo_streak": ante["ante_state"]["combo_streak"],
        "cells_remaining": _cells_remaining(ante),
        "wrong_cells": _wrong_cells(ante),
        "boosts": BOOSTS,
        "hints": ante.get("hints", {}),
        "intel": ante.get("intel", {}),
        "intel_enabled": _intel_enabled(ante),
        "help_budget": max(0, score - target) if target_met else 0,
        "next_shop_label": _next_shop_label(state) if state else "Shop",
        "puzzle_progress": 1.0 - (_cells_remaining(ante) / max(1, sum(1 for r in range(9) for c in range(9) if ante["puzzle"][r][c] == 0))),
    }


def public_state(state: dict) -> dict:
    ante = state.get("ante")
    public_ante = _ante_public(ante, state) if ante else None
    shop = state.get("shop")
    public_shop = None
    if shop:
        public_shop = {
            "tricks": shop["tricks"],
            "kniffs": shop["kniffs"],
            "reroll_cost": shop["reroll_cost"],
        }
    return {
        "run_seed": state["run_seed"],
        "phase": state["phase"],
        "map_index": state["map_index"],
        "map_nodes": state["map_nodes"],
        "hearts": state["hearts"],
        "max_hearts": state["max_hearts"],
        "beute": state["beute"],
        "trick_ids": state["trick_ids"],
        "tricks": [trick_by_id(t) for t in state["trick_ids"]],
        "kniffs": state["kniffs"],
        "antes_completed": state["antes_completed"],
        "ante": public_ante,
        "shop": public_shop,
        "result": state.get("result"),
        "victory": state.get("victory"),
        "pending_kniff": state.get("pending_kniff"),
        "last_quote": state.get("last_quote"),
        "meta": {
            "meta_beute": state["meta"]["meta_beute"],
            "upgrades": state["meta"]["upgrades"],
            "catalog": meta_upgrades(),
        },
    }


def _persist(state: dict) -> None:
    save_run(_serialize(state))


def start_from_map() -> dict:
    state = _hydrate(load_run())
    if state["phase"] != PHASE_MAP:
        return public_state(state)
    _start_ante(state)
    _persist(state)
    return public_state(state)


def place_cell(row: int, col: int, value: int) -> dict:
    state = _hydrate(load_run())
    if state["phase"] != PHASE_ANTE or not state.get("ante"):
        raise ValueError("Kein aktives Ante")

    ante = state["ante"]
    if ante["fixed"][row][col]:
        raise ValueError("Zelle ist fix")
    existing = ante["player_grid"][row][col]
    if existing != 0 and not _is_wrong_player_cell(ante, row, col):
        raise ValueError("Zelle schon belegt")

    solution_val = ante["solution"][row][col]
    correct = value == solution_val
    before = deepcopy(ante["player_grid"])
    ante["player_grid"][row][col] = value

    ante_state = AnteScoreState(**ante["ante_state"])
    score_result = apply_placement_score(
        grid=ante["player_grid"],
        before=before,
        row=row,
        col=col,
        value=value,
        correct=correct,
        trick_ids=state["trick_ids"],
        ante_state=ante_state,
        rng=state["rng"],
    )
    ante["ante_state"] = {
        "combo_streak": ante_state.combo_streak,
        "first_row_done": ante_state.first_row_done,
        "mistakes_forgiven_left": ante_state.mistakes_forgiven_left,
        "cheat_sheet_left": ante_state.cheat_sheet_left,
    }

    events = score_result.events
    if correct:
        bonus = 0
        if "schnellschreiber" in state["trick_ids"] and ante["moves_left"] > 5:
            bonus = 5
            events.append({"type": "trick_proc", "trick_id": "schnellschreiber", "message": "Schnellschreiber +5!"})
        ante["score"] += score_result.points + bonus
    else:
        if not any(e.get("trick_id") == "waschbaer_ablenkung" for e in events):
            state["hearts"] -= 1
            events.append({"type": "heart_lost", "hearts": state["hearts"]})
        events.append({"type": "cell_wrong", "row": row, "col": col, "value": value})

    ante["moves_left"] -= 1
    ante.setdefault("hints", {}).pop(f"{row},{col}", None)
    _clear_cell_intel(ante, row, col)
    if _intel_enabled(ante):
        strip_digit_from_peers(ante, row, col, value)

    if not ante.get("target_met") and ante["score"] >= ante["score_target"]:
        _grant_target_met(ante, events)

    if correct:
        run_auto_fills(state=state, events=events)

    puzzle_done = is_complete(ante["player_grid"])
    lost = state["hearts"] <= 0 or (ante["moves_left"] <= 0 and not puzzle_done)

    if puzzle_done:
        _on_puzzle_complete(state, events)
    elif lost:
        state["phase"] = PHASE_RUN_OVER
        reward = max(2, state["antes_completed"] * 3)
        state["meta"]["meta_beute"] += reward
        state["result"] = {"won": False, "meta_reward": reward, "message": "Waschbär flieht mit leeren Pfoten."}
        clear_run()
        from app.db import save_meta

        save_meta({"meta_beute": state["meta"]["meta_beute"], "upgrades": state["meta"]["upgrades"]})
    else:
        _persist(state)

    if state["phase"] not in (PHASE_RUN_OVER, PHASE_RUN_WON):
        _persist(state)

    response = public_state(state)
    response["events"] = events
    return response


def _on_puzzle_complete(state: dict, events: list[dict]) -> None:
    ante = state["ante"]
    beute_gain = max(4, ante["score"] // 40)
    if is_complete(ante["player_grid"]):
        beute_gain += 6
    if "ticket_magnet" in state["trick_ids"]:
        beute_gain = int(beute_gain * 1.2)
    state["beute"] += beute_gain
    state["antes_completed"] += 1
    is_boss = MAP_NODES[state["map_index"]]["type"] == "boss"
    message = "Gitter geknackt! " + random_quote(state["rng"])
    events.append({
        "type": "ante_won",
        "beute_gain": beute_gain,
        "message": message,
    })
    state["phase"] = PHASE_ANTE_VICTORY
    state["victory"] = {
        "message": message,
        "beute_gain": beute_gain,
        "is_boss": is_boss,
    }


def advance_from_victory() -> dict:
    state = _hydrate(load_run())
    if state["phase"] != PHASE_ANTE_VICTORY:
        raise ValueError("Kein Sieg aktiv")

    victory = state.pop("victory", {})
    is_boss = victory.get("is_boss", False)

    if is_boss:
        state["phase"] = PHASE_RUN_WON
        reward = 20 + state["antes_completed"] * 5
        state["meta"]["meta_beute"] += reward
        state["result"] = {"won": True, "meta_reward": reward, "message": "HAUPTTRESOR GEPLÜNDERT!"}
        clear_run()
        from app.db import save_meta

        save_meta({"meta_beute": state["meta"]["meta_beute"], "upgrades": state["meta"]["upgrades"]})
    else:
        state["map_index"] += 1
        next_node = MAP_NODES[state["map_index"]]
        if next_node["type"] == "shop":
            _open_shop(state)
        else:
            _start_ante(state)
        _persist(state)

    return public_state(state)


def clear_cell(row: int, col: int) -> dict:
    state = _hydrate(load_run())
    if state["phase"] != PHASE_ANTE or not state.get("ante"):
        raise ValueError("Kein aktives Ante")

    ante = state["ante"]
    if ante["fixed"][row][col]:
        raise ValueError("Zelle ist fix")

    existing = ante["player_grid"][row][col]
    if existing == 0:
        raise ValueError("Zelle ist leer")

    is_wrong = _is_wrong_player_cell(ante, row, col)
    pending_radier = state.get("pending_kniff") == "radiergummi"
    if not is_wrong:
        raise ValueError("Nur falsche Eingaben löschbar")
    if pending_radier:
        state["kniffs"]["radiergummi"] -= 1
        state.pop("pending_kniff", None)

    ante["player_grid"][row][col] = 0
    _clear_cell_intel(ante, row, col)
    if _intel_enabled(ante):
        valid = valid_candidates(ante, row, col)
        if valid:
            ante.setdefault("intel", {})[f"{row},{col}"] = sorted(valid)
    events = [{"type": "cell_cleared", "row": row, "col": col, "message": "Falsche Zahl entfernt."}]
    _persist(state)
    out = public_state(state)
    out["events"] = events
    return out


def toggle_intel_note(row: int, col: int, digit: int) -> dict:
    state = _hydrate(load_run())
    if state["phase"] != PHASE_ANTE or not state.get("ante"):
        raise ValueError("Kein aktives Ante")

    ante = state["ante"]
    if not _intel_enabled(ante):
        raise ValueError("INTEL erst ab mittlerer Schwierigkeit")
    if ante["fixed"][row][col]:
        raise ValueError("Zelle ist fix")
    if ante["player_grid"][row][col] != 0 and not _is_wrong_player_cell(ante, row, col):
        raise ValueError("Zelle ist belegt")

    hints = ante.get("hints", {})
    if hints.get(f"{row},{col}"):
        raise ValueError("50/50 aktiv — erst wählen")

    notes = ante.setdefault("intel", {})
    key = f"{row},{col}"
    current = set(notes.get(key, []))
    valid = valid_candidates(ante, row, col)
    if digit in current:
        current.remove(digit)
    else:
        if digit not in valid:
            raise ValueError("Zahl hier blockiert")
        current.add(digit)
    if current:
        notes[key] = sorted(current)
    else:
        notes.pop(key, None)

    _persist(state)
    out = public_state(state)
    out["events"] = [{"type": "intel_toggle", "row": row, "col": col, "digit": digit}]
    return out


def sync_intel() -> dict:
    state = _hydrate(load_run())
    if state["phase"] != PHASE_ANTE or not state.get("ante"):
        raise ValueError("Kein aktives Ante")

    ante = state["ante"]
    if not _intel_enabled(ante):
        raise ValueError("INTEL erst ab mittlerer Schwierigkeit")

    refresh_intel(ante, fill_all=True)
    _persist(state)
    out = public_state(state)
    out["events"] = [{"type": "intel_sync", "message": "Wiretap synchronisiert."}]
    return out


def buy_boost(boost_id: str, row: int | None, col: int | None) -> dict:
    state = _hydrate(load_run())
    if state["phase"] != PHASE_ANTE or not state.get("ante"):
        raise ValueError("Kein aktives Ante")

    ante = state["ante"]
    if not ante.get("target_met"):
        raise ValueError("Erst das Punkteziel erreichen")

    boost = boost_by_id(boost_id)
    if not boost:
        raise ValueError("Boost unbekannt")

    events: list[dict] = []

    if boost_id == "extra_moves":
        spend_score(ante, boost["cost"])
        ante["moves_left"] += 5
        events.append({"type": "boost_used", "boost_id": boost_id, "message": "+5 Züge gekauft!"})
    elif boost_id == "fifty_fifty":
        if row is None or col is None:
            raise ValueError("Zelle für 50/50 wählen")
        if ante["fixed"][row][col] or ante["player_grid"][row][col] != 0:
            raise ValueError("Zelle muss leer sein")
        spend_score(ante, boost["cost"])
        correct = ante["solution"][row][col]
        a, b = fifty_fifty_options(correct, state["rng"])
        key = f"{row},{col}"
        ante.setdefault("hints", {})[key] = [a, b]
        events.append({
            "type": "fifty_fifty",
            "row": row,
            "col": col,
            "options": [a, b],
            "message": "50/50 — Ecke antippen!",
        })
    elif boost_id == "reveal":
        if row is None or col is None:
            raise ValueError("Zelle für Einblick wählen")
        if ante["fixed"][row][col] or ante["player_grid"][row][col] != 0:
            raise ValueError("Zelle muss leer sein")
        spend_score(ante, boost["cost"])
        val = ante["solution"][row][col]
        ante["player_grid"][row][col] = val
        ante["fixed"][row][col] = True
        ante.setdefault("hints", {}).pop(f"{row},{col}", None)
        events.append({
            "type": "reveal",
            "row": row,
            "col": col,
            "value": val,
            "message": "Einblick — Zelle aufgedeckt!",
        })
        run_auto_fills(state=state, events=events)
        if is_complete(ante["player_grid"]):
            _on_puzzle_complete(state, events)
    else:
        raise ValueError("Boost nicht implementiert")

    _persist(state)
    out = public_state(state)
    out["events"] = events
    return out


def _open_shop(state: dict) -> None:
    meta_reroll = upgrade_level(state["meta"]["upgrades"], "shop_reroll")
    state["shop"] = generate_shop_offers_with_meta(state["trick_ids"], state["rng"], meta_reroll)
    state["phase"] = PHASE_SHOP
    state["last_quote"] = random_quote(state["rng"])


def shop_buy(item_id: str, kind: str) -> dict:
    state = _hydrate(load_run())
    if state["phase"] != PHASE_SHOP or not state.get("shop"):
        raise ValueError("Kein Shop aktiv")

    shop = state["shop"]
    pool = shop["tricks"] if kind == "trick" else shop["kniffs"]
    item = next((i for i in pool if i["id"] == item_id), None)
    if not item:
        raise ValueError("Item nicht im Angebot")
    if state["beute"] < item["cost"]:
        raise ValueError("Nicht genug Beute")

    state["beute"] -= item["cost"]
    if kind == "trick":
        if item_id in state["trick_ids"]:
            raise ValueError("Trick schon owned")
        state["trick_ids"].append(item_id)
        state["max_hearts"] = _max_hearts(state["trick_ids"], upgrade_level(state["meta"]["upgrades"], "extra_heart"))
        state["hearts"] = min(state["hearts"] + (1 if item_id == "waschbaers_tasche" else 0), state["max_hearts"])
    else:
        state["kniffs"][item_id] = state["kniffs"].get(item_id, 0) + 1

    _persist(state)
    return public_state(state)


def shop_reroll() -> dict:
    state = _hydrate(load_run())
    if state["phase"] != PHASE_SHOP:
        raise ValueError("Kein Shop aktiv")
    cost = state["shop"]["reroll_cost"]
    if state["beute"] < cost:
        raise ValueError("Nicht genug Beute")
    state["beute"] -= cost
    meta_reroll = upgrade_level(state["meta"]["upgrades"], "shop_reroll")
    state["shop"] = generate_shop_offers_with_meta(state["trick_ids"], state["rng"], meta_reroll)
    _persist(state)
    return public_state(state)


def ante_continue() -> dict:
    state = _hydrate(load_run())
    if state["phase"] != PHASE_SHOP:
        raise ValueError("Nicht im Shop")
    state["map_index"] += 1
    if state["map_index"] >= len(MAP_NODES):
        state["phase"] = PHASE_RUN_WON
        _persist(state)
        return public_state(state)
    node = MAP_NODES[state["map_index"]]
    if node["type"] == "shop":
        _open_shop(state)
    else:
        _start_ante(state)
    _persist(state)
    return public_state(state)


def use_kniff(kniff_id: str) -> dict:
    state = _hydrate(load_run())
    if state["kniffs"].get(kniff_id, 0) <= 0:
        raise ValueError("Kniff nicht vorhanden")
    events: list[dict] = []

    if kniff_id == "beute_boost" and state["phase"] == PHASE_ANTE:
        state["ante"]["score"] += 30
        events.append({"type": "trick_proc", "message": "Beute-Boost +30 Punkte!"})
    elif kniff_id == "herz_pflaster":
        state["hearts"] = min(state["hearts"] + 1, state["max_hearts"])
        events.append({"type": "trick_proc", "message": "Herz-Pflaster klebt!"})
    elif kniff_id == "schummel_zettel" and state["phase"] == PHASE_ANTE:
        ante = state["ante"]
        empty = [(r, c) for r in range(9) for c in range(9) if ante["player_grid"][r][c] == 0 and not ante["fixed"][r][c]]
        if empty:
            r, c = state["rng"].choice(empty)
            val = ante["solution"][r][c]
            resp = place_cell(r, c, val)
            state = _hydrate(load_run())
            state["kniffs"][kniff_id] -= 1
            _persist(state)
            out = public_state(state)
            out["events"] = resp.get("events", []) + [{"type": "trick_proc", "message": "Schummel-Zettel hilft!"}]
            return out
    elif kniff_id == "radiergummi" and state["phase"] == PHASE_ANTE:
        events.append({"type": "trick_proc", "message": "Radiergummi bereit — tippe eine falsche Zelle zum Löschen."})
        state["pending_kniff"] = "radiergummi"
        _persist(state)
        out = public_state(state)
        out["events"] = events
        return out
    else:
        raise ValueError("Kniff hier nicht nutzbar")

    state["kniffs"][kniff_id] -= 1
    _persist(state)
    out = public_state(state)
    out["events"] = events
    return out


def buy_meta_upgrade(upgrade_id: str) -> dict:
    from app.db import save_meta

    meta = get_meta()
    catalog = {u["id"]: u for u in meta_upgrades()}
    if upgrade_id not in catalog:
        raise ValueError("Upgrade unbekannt")
    item = catalog[upgrade_id]
    level = upgrade_level(meta["upgrades"], upgrade_id)
    if level >= item["max_level"]:
        raise ValueError("Max Level erreicht")
    if meta["meta_beute"] < item["cost"]:
        raise ValueError("Nicht genug Meta-Beute")
    meta["meta_beute"] -= item["cost"]
    meta["upgrades"][upgrade_id] = level + 1
    save_meta(meta)
    return {"meta_beute": meta["meta_beute"], "upgrades": meta["upgrades"], "catalog": meta_upgrades()}


def has_active_run() -> bool:
    return load_run() is not None
