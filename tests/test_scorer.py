"""Tests for scoring."""

from app.sudoku.scorer import AnteScoreState, apply_placement_score, score_target_for_ante


def _grid():
    return [[0] * 9 for _ in range(9)]


def test_correct_cell_gives_points():
    grid = _grid()
    before = _grid()
    grid[0][0] = 5
    state = AnteScoreState()
    import random

    result = apply_placement_score(
        grid=grid,
        before=before,
        row=0,
        col=0,
        value=5,
        correct=True,
        trick_ids=[],
        ante_state=state,
        rng=random.Random(1),
    )
    assert result.points >= 10
    assert state.combo_streak == 1


def test_dreihaus_vampir_bonus():
    grid = _grid()
    before = _grid()
    grid[0][0] = 3
    state = AnteScoreState()
    import random

    result = apply_placement_score(
        grid=grid,
        before=before,
        row=0,
        col=0,
        value=3,
        correct=True,
        trick_ids=["dreihaus_vampir"],
        ante_state=state,
        rng=random.Random(1),
    )
    assert result.points >= 35


def test_waschbaers_tasche_raises_target():
    base = score_target_for_ante(0, False, [])
    boosted = score_target_for_ante(0, False, ["waschbaers_tasche"])
    assert boosted > base
