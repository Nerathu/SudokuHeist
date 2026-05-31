"""Tests for auto-fill."""

from app.game.autofill import find_auto_fill


def test_find_auto_fill_row():
    ante = {
        "player_grid": [
            [1, 2, 3, 4, 5, 6, 7, 8, 0],
            [0] * 9,
            [0] * 9,
            [0] * 9,
            [0] * 9,
            [0] * 9,
            [0] * 9,
            [0] * 9,
            [0] * 9,
        ],
        "fixed": [[False] * 9 for _ in range(9)],
        "solution": [[9 if c == 8 else 0 for c in range(9)] if r == 0 else [0] * 9 for r in range(9)],
    }
    ante["solution"][0] = [1, 2, 3, 4, 5, 6, 7, 8, 9]
    hit = find_auto_fill(ante)
    assert hit == (0, 8, 9)
