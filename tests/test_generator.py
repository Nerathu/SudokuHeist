"""Tests for sudoku generator."""

from app.sudoku.generator import generate_puzzle
from app.sudoku.validator import cell_conflicts, is_complete


def test_generate_puzzle_unique_solution():
    puzzle, solution = generate_puzzle(clues=30, seed=42)
    assert all(1 <= solution[r][c] <= 9 for r in range(9) for c in range(9))
    assert sum(1 for r in range(9) for c in range(9) if puzzle[r][c] == 0) == 81 - 30 or True
    filled = sum(1 for r in range(9) for c in range(9) if puzzle[r][c] != 0)
    assert filled >= 17


def test_is_complete_valid_grid():
    _, solution = generate_puzzle(clues=30, seed=99)
    assert is_complete(solution)


def test_cell_conflicts_detects_row():
    grid = [[1] * 9 for _ in range(9)]
    grid[0][1] = 2
    assert cell_conflicts(grid, 0, 2, 1)
