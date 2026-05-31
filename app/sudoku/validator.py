"""Sudoku validation helpers."""

from __future__ import annotations


def cell_conflicts(grid: list[list[int]], row: int, col: int, value: int) -> bool:
    if value == 0:
        return False
    for c in range(9):
        if c != col and grid[row][c] == value:
            return True
    for r in range(9):
        if r != row and grid[r][col] == value:
            return True
    br, bc = 3 * (row // 3), 3 * (col // 3)
    for r in range(br, br + 3):
        for c in range(bc, bc + 3):
            if (r, c) != (row, col) and grid[r][c] == value:
                return True
    return False


def is_complete(grid: list[list[int]]) -> bool:
    for row in range(9):
        for col in range(9):
            if grid[row][col] == 0:
                return False
            if cell_conflicts(grid, row, col, grid[row][col]):
                return False
    return True


def row_complete(grid: list[list[int]], row: int) -> bool:
    if any(grid[row][c] == 0 for c in range(9)):
        return False
    return len(set(grid[row])) == 9


def col_complete(grid: list[list[int]], col: int) -> bool:
    if any(grid[r][col] == 0 for r in range(9)):
        return False
    return len(set(grid[r][col] for r in range(9))) == 9


def block_complete(grid: list[list[int]], row: int, col: int) -> bool:
    br, bc = 3 * (row // 3), 3 * (col // 3)
    values = []
    for r in range(br, br + 3):
        for c in range(bc, bc + 3):
            if grid[r][c] == 0:
                return False
            values.append(grid[r][c])
    return len(set(values)) == 9


def newly_complete_units(
    grid: list[list[int]], before: list[list[int]], row: int, col: int
) -> dict[str, list[int]]:
    result: dict[str, list[int]] = {"rows": [], "cols": [], "blocks": []}
    if not row_complete(grid, row) or row_complete(before, row):
        pass
    else:
        result["rows"].append(row)
    if not col_complete(grid, col) or col_complete(before, col):
        pass
    else:
        result["cols"].append(col)
    br, bc = 3 * (row // 3), 3 * (col // 3)
    block_id = (br // 3) * 3 + (bc // 3)
    if block_complete(grid, row, col) and not block_complete(before, row, col):
        result["blocks"].append(block_id)
    return result
