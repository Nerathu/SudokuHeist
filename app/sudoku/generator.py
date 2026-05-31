"""Sudoku puzzle generation."""

from __future__ import annotations

import random
from copy import deepcopy


def _empty_grid() -> list[list[int]]:
    return [[0] * 9 for _ in range(9)]


def _is_valid(grid: list[list[int]], row: int, col: int, value: int) -> bool:
    if value in grid[row]:
        return False
    if any(grid[r][col] == value for r in range(9)):
        return False
    br, bc = 3 * (row // 3), 3 * (col // 3)
    for r in range(br, br + 3):
        for c in range(bc, bc + 3):
            if grid[r][c] == value:
                return False
    return True


def _solve(grid: list[list[int]], rng: random.Random | None = None) -> bool:
    for row in range(9):
        for col in range(9):
            if grid[row][col] != 0:
                continue
            values = list(range(1, 10))
            if rng:
                rng.shuffle(values)
            else:
                random.shuffle(values)
            for value in values:
                if _is_valid(grid, row, col, value):
                    grid[row][col] = value
                    if _solve(grid, rng):
                        return True
                    grid[row][col] = 0
            return False
    return True


def _count_solutions(grid: list[list[int]], limit: int = 2) -> int:
    count = 0

    def backtrack() -> None:
        nonlocal count
        if count >= limit:
            return
        for row in range(9):
            for col in range(9):
                if grid[row][col] != 0:
                    continue
                for value in range(1, 10):
                    if _is_valid(grid, row, col, value):
                        grid[row][col] = value
                        backtrack()
                        grid[row][col] = 0
                        if count >= limit:
                            return
                return
        count += 1

    backtrack()
    return count


def generate_puzzle(clues: int = 30, seed: int | None = None) -> tuple[list[list[int]], list[list[int]]]:
    """Return (puzzle with 0 for empty, solution grid). clues = number of prefilled cells."""
    rng = random.Random(seed)
    solution = _empty_grid()
    _solve(solution, rng)

    puzzle = deepcopy(solution)
    cells = [(r, c) for r in range(9) for c in range(9)]
    rng.shuffle(cells)

    target_removed = 81 - max(17, min(64, clues))
    removed = 0
    for row, col in cells:
        if removed >= target_removed:
            break
        backup = puzzle[row][col]
        puzzle[row][col] = 0
        test = deepcopy(puzzle)
        if _count_solutions(test, limit=2) == 1:
            removed += 1
        else:
            puzzle[row][col] = backup

    return puzzle, deepcopy(solution)


def clues_for_difficulty(difficulty: str) -> int:
    return {"easy": 40, "medium": 30, "hard": 22, "boss": 20}.get(difficulty, 30)
