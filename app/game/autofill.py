"""Auto-fill when a row, column, or block has only one empty cell."""

from __future__ import annotations

from copy import deepcopy

from app.game.balance import HELP_BONUS_SCORE
from app.sudoku.scorer import AnteScoreState, apply_placement_score


def _sole_empty_and_digit(cells: list[tuple[int, int, int]]) -> tuple[int, int, int] | None:
    empties = [(r, c) for r, c, v in cells if v == 0]
    if len(empties) != 1:
        return None
    present = {v for _, _, v in cells if v != 0}
    missing = list(set(range(1, 10)) - present)
    if len(missing) != 1:
        return None
    r, c = empties[0]
    return r, c, missing[0]


def find_auto_fill(ante: dict) -> tuple[int, int, int] | None:
    grid = ante["player_grid"]
    fixed = ante["fixed"]

    for r in range(9):
        cells = [(r, c, grid[r][c]) for c in range(9)]
        hit = _sole_empty_and_digit(cells)
        if hit and not fixed[hit[0]][hit[1]] and grid[hit[0]][hit[1]] == 0:
            return hit

    for c in range(9):
        cells = [(r, c, grid[r][c]) for r in range(9)]
        hit = _sole_empty_and_digit(cells)
        if hit and not fixed[hit[0]][hit[1]] and grid[hit[0]][hit[1]] == 0:
            return hit

    for br in range(0, 9, 3):
        for bc in range(0, 9, 3):
            cells = [
                (r, col, grid[r][col])
                for r in range(br, br + 3)
                for col in range(bc, bc + 3)
            ]
            hit = _sole_empty_and_digit(cells)
            if hit and not fixed[hit[0]][hit[1]] and grid[hit[0]][hit[1]] == 0:
                return hit

    return None


def apply_auto_fill_once(*, state: dict, ante: dict, events: list[dict]) -> bool:
    hit = find_auto_fill(ante)
    if not hit:
        return False

    row, col, value = hit
    if value != ante["solution"][row][col]:
        return False

    before = deepcopy(ante["player_grid"])
    ante["player_grid"][row][col] = value
    ante.setdefault("hints", {}).pop(f"{row},{col}", None)
    ante.setdefault("intel", {}).pop(f"{row},{col}", None)

    ante_state = AnteScoreState(**ante["ante_state"])
    score_result = apply_placement_score(
        grid=ante["player_grid"],
        before=before,
        row=row,
        col=col,
        value=value,
        correct=True,
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

    bonus = 0
    if "schnellschreiber" in state["trick_ids"] and ante["moves_left"] > 5:
        bonus = 5
    ante["score"] += score_result.points + bonus

    events.append({"type": "auto_fill", "row": row, "col": col, "value": value})
    events.extend(score_result.events)
    return True


def run_auto_fills(*, state: dict, events: list[dict]) -> None:
    ante = state["ante"]
    while apply_auto_fill_once(state=state, ante=ante, events=events):
        if not ante.get("target_met") and ante["score"] >= ante["score_target"]:
            ante["target_met"] = True
            ante["score"] += HELP_BONUS_SCORE
            events.append({
                "type": "target_met",
                "message": f"Beute gesichert! +{HELP_BONUS_SCORE} Hilfe-Punkte — Boosts freigeschaltet.",
                "help_bonus": HELP_BONUS_SCORE,
            })
