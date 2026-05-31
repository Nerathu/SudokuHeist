"""Tests for INTEL candidate logic."""

import os
import tempfile

import pytest

from app.db import init_db, load_run, save_meta, save_run
from app.game import run as run_service
from app.game.intel import refresh_intel, valid_candidates


@pytest.fixture
def temp_db(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "test.db")
        monkeypatch.setenv("DB_PATH", db_path)
        init_db()
        save_meta({"meta_beute": 0, "upgrades": {}})
        yield db_path


def _start_medium_ante():
    run_service.new_run(seed=4242)
    raw = load_run()
    raw["map_index"] = 3
    save_run(raw)
    return run_service.start_from_map()


def test_sync_intel_fills_only_valid_candidates(temp_db):
    state = _start_medium_ante()
    synced = run_service.sync_intel()
    ante = synced["ante"]
    grid = ante["player_grid"]
    intel = ante["intel"]

    for r in range(9):
        for c in range(9):
            if grid[r][c] != 0:
                assert f"{r},{c}" not in intel
                continue
            notes = set(intel.get(f"{r},{c}", []))
            assert notes == valid_candidates(
                {"player_grid": grid, "fixed": ante["fixed"]},
                r,
                c,
            )


def test_place_strips_digit_from_peer_intel(temp_db):
    state = _start_medium_ante()
    run_service.sync_intel()
    raw = load_run()
    solution = raw["ante"]["solution"]
    grid = raw["ante"]["player_grid"]
    r, c = next((r, c) for r in range(9) for c in range(9) if grid[r][c] == 0)
    value = solution[r][c]

    before = set(raw["ante"]["intel"].get(f"{r},0", []))
    assert value in before or f"{r},0" not in raw["ante"]["intel"]

    run_service.place_cell(r, c, value)
    raw = load_run()
    peer_notes = raw["ante"]["intel"].get(f"{r},0", [])
    assert value not in peer_notes


def test_toggle_rejects_blocked_digit(temp_db):
    state = _start_medium_ante()
    raw = load_run()
    grid = state["ante"]["player_grid"]
    r, c = next((ri, ci) for ri in range(9) for ci in range(9) if grid[ri][ci] == 0)
    blocked = next(iter(valid_candidates(raw["ante"], r, c)))
    # occupy same row with a wrong value that blocks `blocked`
    oc = next(ci for ci in range(9) if ci != c and grid[r][ci] == 0)
    raw["ante"]["player_grid"][r][oc] = blocked
    save_run(raw)

    with pytest.raises(ValueError, match="blockiert"):
        run_service.toggle_intel_note(r, c, blocked)


def test_refresh_intel_prunes_existing_notes(temp_db):
    state = _start_medium_ante()
    raw = load_run()
    ante = raw["ante"]
    grid = ante["player_grid"]
    r, c = next((ri, ci) for ri in range(9) for ci in range(9) if grid[ri][ci] == 0)
    ante["intel"] = {f"{r},{c}": list(range(1, 10))}
    refresh_intel(ante, fill_all=False)
    assert set(ante["intel"][f"{r},{c}"]) == valid_candidates(ante, r, c)
