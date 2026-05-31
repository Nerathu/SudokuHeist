"""INTEL Wiretap — candidate notes from Sudoku constraints."""

from __future__ import annotations

import json


def peer_cells(row: int, col: int) -> list[tuple[int, int]]:
    peers: list[tuple[int, int]] = []
    for c in range(9):
        if c != col:
            peers.append((row, c))
    for r in range(9):
        if r != row:
            peers.append((r, col))
    br, bc = (row // 3) * 3, (col // 3) * 3
    for r in range(br, br + 3):
        for c in range(bc, bc + 3):
            if (r, c) != (row, col):
                peers.append((r, c))
    return peers


def occupied_digits(ante: dict, row: int, col: int) -> set[int]:
    grid = ante["player_grid"]
    seen: set[int] = set()
    for c in range(9):
        v = grid[row][c]
        if v:
            seen.add(v)
    for r in range(9):
        v = grid[r][col]
        if v:
            seen.add(v)
    br, bc = (row // 3) * 3, (col // 3) * 3
    for r in range(br, br + 3):
        for c in range(bc, bc + 3):
            v = grid[r][c]
            if v:
                seen.add(v)
    return seen


def valid_candidates(ante: dict, row: int, col: int) -> set[int]:
    if ante["fixed"][row][col] or ante["player_grid"][row][col] != 0:
        return set()
    return set(range(1, 10)) - occupied_digits(ante, row, col)


def strip_digit_from_peers(ante: dict, row: int, col: int, digit: int) -> None:
    intel = ante.setdefault("intel", {})
    for pr, pc in peer_cells(row, col):
        key = f"{pr},{pc}"
        if key not in intel:
            continue
        pruned = [d for d in intel[key] if d != digit]
        if pruned:
            intel[key] = pruned
        else:
            intel.pop(key)


def refresh_intel(ante: dict, *, fill_all: bool = False) -> None:
    """Drop impossible notes; optionally fill every empty cell with valid candidates."""
    intel = ante.setdefault("intel", {})
    hints = ante.get("hints", {})
    for r in range(9):
        for c in range(9):
            key = f"{r},{c}"
            if hints.get(key) or ante["player_grid"][r][c] != 0:
                intel.pop(key, None)
                continue
            valid = valid_candidates(ante, r, c)
            if fill_all:
                if valid:
                    intel[key] = sorted(valid)
                else:
                    intel.pop(key, None)
            elif key in intel:
                pruned = sorted(set(intel[key]) & valid)
                if pruned:
                    intel[key] = pruned
                else:
                    intel.pop(key, None)


def maintain_intel(ante: dict) -> bool:
    """Re-sync all wiretap notes with the live grid. Returns True if intel changed."""
    intel = ante.get("intel")
    if not intel:
        return False
    before = json.dumps(intel, sort_keys=True)
    refresh_intel(ante, fill_all=True)
    return json.dumps(ante.get("intel", {}), sort_keys=True) != before


def intel_notes_valid(ante: dict) -> bool:
    """True when every stored note is still a legal candidate."""
    intel = ante.get("intel") or {}
    hints = ante.get("hints") or {}
    for key, notes in intel.items():
        r, c = map(int, key.split(","))
        if hints.get(key) or ante["player_grid"][r][c] != 0:
            continue
        allowed = valid_candidates(ante, r, c)
        if any(n not in allowed for n in notes):
            return False
    return True
