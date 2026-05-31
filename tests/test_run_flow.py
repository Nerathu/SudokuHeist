"""Integration tests for run flow."""

import os
import tempfile

import pytest

from app.db import init_db, save_meta
from app.game import run as run_service


@pytest.fixture
def temp_db(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "test.db")
        monkeypatch.setenv("DB_PATH", db_path)
        init_db()
        save_meta({"meta_beute": 0, "upgrades": {}})
        yield db_path


def test_new_run_and_start(temp_db):
    state = run_service.new_run(seed=123)
    assert state["phase"] == "map"
    started = run_service.start_from_map()
    assert started["phase"] == "ante"
    assert started["ante"]["player_grid"] is not None


def test_place_correct_cell(temp_db):
    run_service.new_run(seed=456)
    state = run_service.start_from_map()
    grid = state["ante"]["player_grid"]
    for r in range(9):
        for c in range(9):
            if grid[r][c] == 0:
                from app.db import load_run

                raw = load_run()
                solution = raw["ante"]["solution"]
                result = run_service.place_cell(r, c, solution[r][c])
                assert "events" in result
                return
    pytest.fail("No empty cell found")


def _wrong_value(solution_val: int) -> int:
    return (solution_val % 9) + 1


def test_clear_and_overwrite_wrong_cell(temp_db):
    run_service.new_run(seed=789)
    state = run_service.start_from_map()
    from app.db import load_run

    raw = load_run()
    solution = raw["ante"]["solution"]
    grid = state["ante"]["player_grid"]
    r, c = next((r, c) for r in range(9) for c in range(9) if grid[r][c] == 0)
    wrong = _wrong_value(solution[r][c])

    placed = run_service.place_cell(r, c, wrong)
    assert [r, c] in placed["ante"]["wrong_cells"]

    cleared = run_service.clear_cell(r, c)
    assert cleared["ante"]["player_grid"][r][c] == 0

    run_service.place_cell(r, c, wrong)
    fixed = run_service.place_cell(r, c, solution[r][c])
    assert fixed["ante"]["player_grid"][r][c] == solution[r][c]
    assert [r, c] not in fixed["ante"]["wrong_cells"]


def test_victory_phase_before_shop(temp_db):
    from app.db import load_run, save_run

    run_service.new_run(seed=111)
    run_service.start_from_map()
    raw = load_run()
    raw["phase"] = run_service.PHASE_ANTE_VICTORY
    raw["victory"] = {"is_boss": False, "beute_gain": 10, "message": "Test-Sieg"}
    save_run(raw)

    advanced = run_service.advance_from_victory()
    assert advanced["phase"] in ("shop", "ante")
    assert advanced.get("victory") is None
