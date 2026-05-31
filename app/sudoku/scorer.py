"""Score calculation with trick effects."""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from app.sudoku.validator import newly_complete_units


BASE_CELL_SCORE = 10
ROW_BONUS = 30
COL_BONUS = 30
BLOCK_BONUS = 20
BLOCK_BOSS_BONUS = 50


@dataclass
class ScoreResult:
    points: int = 0
    multiplier: float = 1.0
    events: list[dict] = field(default_factory=list)
    combo_streak: int = 0


@dataclass
class AnteScoreState:
    combo_streak: int = 0
    first_row_done: bool = False
    mistakes_forgiven_left: int = 0
    cheat_sheet_left: int = 0


def _has_trick(trick_ids: list[str], trick_id: str) -> bool:
    return trick_id in trick_ids


def apply_placement_score(
    *,
    grid: list[list[int]],
    before: list[list[int]],
    row: int,
    col: int,
    value: int,
    correct: bool,
    trick_ids: list[str],
    ante_state: AnteScoreState,
    rng: random.Random,
) -> ScoreResult:
    result = ScoreResult(combo_streak=ante_state.combo_streak)

    if not correct:
        if ante_state.mistakes_forgiven_left > 0:
            ante_state.mistakes_forgiven_left -= 1
            result.events.append({"type": "trick_proc", "trick_id": "waschbaer_ablenkung", "message": "Waschbär lenkt ab — kein Herzverlust!"})
            return result
        ante_state.combo_streak = 0
        result.combo_streak = 0
        result.events.append({"type": "combo_break"})
        return result

    ante_state.combo_streak += 1
    result.combo_streak = ante_state.combo_streak

    points = BASE_CELL_SCORE
    multiplier = 1.0

    if _has_trick(trick_ids, "gerade_gier") and value % 2 == 0:
        points *= 2
        result.events.append({"type": "trick_proc", "trick_id": "gerade_gier", "message": "Gerade Gier verdoppelt!"})

    if _has_trick(trick_ids, "dreihaus_vampir") and value == 3:
        points += 25
        result.events.append({"type": "trick_proc", "trick_id": "dreihaus_vampir", "message": "Dreihaus-Vampir saugt +25!"})

    if _has_trick(trick_ids, "combo_kaffee"):
        bonus_mult = min(5.0, 1.0 + ante_state.combo_streak * 0.25)
        multiplier = max(multiplier, bonus_mult)
        if ante_state.combo_streak > 1:
            result.events.append({"type": "trick_proc", "trick_id": "combo_kaffee", "message": f"Combo-Kaffee ×{bonus_mult:.2f}!"})

    if _has_trick(trick_ids, "raccoon_luck") and rng.random() < 0.15:
        jackpot = 100
        points += jackpot
        result.events.append({"type": "jackpot", "points": jackpot, "message": "JACKPOT! Waschbär klaut die Bank!"})

    if _has_trick(trick_ids, "chaos_nachbar"):
        neighbor_bonus = 0
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = row + dr, col + dc
            if 0 <= nr < 9 and 0 <= nc < 9 and before[nr][nc] != 0:
                neighbor_bonus += 5
        if neighbor_bonus:
            points += neighbor_bonus
            result.events.append({"type": "trick_proc", "trick_id": "chaos_nachbar", "message": f"Chaos-Nachbar +{neighbor_bonus}!"})

    units = newly_complete_units(grid, before, row, col)
    unit_points = 0
    for r in units["rows"]:
        bonus = ROW_BONUS
        if _has_trick(trick_ids, "reihen_rakete") and not ante_state.first_row_done:
            bonus *= 2
            ante_state.first_row_done = True
            result.events.append({"type": "trick_proc", "trick_id": "reihen_rakete", "message": "Reihen-Rakete explodiert!"})
        unit_points += bonus
        result.events.append({"type": "row_complete", "row": r, "points": bonus})
    for c in units["cols"]:
        unit_points += COL_BONUS
        result.events.append({"type": "col_complete", "col": c, "points": COL_BONUS})
    for b in units["blocks"]:
        bonus = BLOCK_BOSS_BONUS if _has_trick(trick_ids, "block_boss") else BLOCK_BONUS
        unit_points += bonus
        result.events.append({"type": "block_complete", "block": b, "points": bonus})
        if _has_trick(trick_ids, "block_boss"):
            result.events.append({"type": "trick_proc", "trick_id": "block_boss", "message": "Block-Boss dominiert!"})

    if _has_trick(trick_ids, "neon_sieben") and value == 7:
        unit_points += 15
        result.events.append({"type": "trick_proc", "trick_id": "neon_sieben", "message": "Neon-Sieben leuchtet wild!"})

    total = int((points + unit_points) * multiplier)
    result.points = total
    result.multiplier = multiplier
    if correct:
        result.events.insert(0, {"type": "cell_correct", "row": row, "col": col, "value": value, "points": total})
    return result


def score_target_for_ante(ante_index: int, is_boss: bool, trick_ids: list[str]) -> int:
    base = [180, 260, 340, 420, 500, 650]
    idx = min(ante_index, len(base) - 1)
    target = base[idx]
    if is_boss:
        target = int(target * 1.2)
    if _has_trick(trick_ids, "waschbaers_tasche"):
        target = int(target * 1.1)
    return target
