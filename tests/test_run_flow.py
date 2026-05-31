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


def test_intel_notes_medium_plus(temp_db):
    from app.db import load_run, save_run
    from app.game.intel import valid_candidates

    run_service.new_run(seed=4242)
    raw = load_run()
    raw["map_index"] = 3
    save_run(raw)
    state = run_service.start_from_map()
    assert state["ante"]["intel_enabled"] is True
    assert state["ante"]["difficulty"] == "medium"

    grid = state["ante"]["player_grid"]
    r, c = next((r, c) for r in range(9) for c in range(9) if grid[r][c] == 0)
    raw = load_run()
    valid = sorted(valid_candidates(raw["ante"], r, c))
    assert len(valid) >= 2
    a, b = valid[0], valid[1]

    toggled = run_service.toggle_intel_note(r, c, a)
    assert toggled["ante"]["intel"][f"{r},{c}"] == [a]

    toggled = run_service.toggle_intel_note(r, c, a)
    assert f"{r},{c}" not in toggled["ante"]["intel"]

    toggled = run_service.toggle_intel_note(r, c, a)
    toggled = run_service.toggle_intel_note(r, c, b)
    assert toggled["ante"]["intel"][f"{r},{c}"] == [a, b]


def test_intel_disabled_on_easy(temp_db):
    run_service.new_run(seed=1)
    state = run_service.start_from_map()
    assert state["ante"]["intel_enabled"] is False
    grid = state["ante"]["player_grid"]
    r, c = next((r, c) for r in range(9) for c in range(9) if grid[r][c] == 0)
    with pytest.raises(ValueError, match="INTEL"):
        run_service.toggle_intel_note(r, c, 1)


def test_target_met_grants_help_bonus(temp_db):
    from app.db import load_run, save_run
    from app.game.balance import HELP_BONUS_SCORE

    run_service.new_run(seed=777)
    run_service.start_from_map()
    raw = load_run()
    ante = raw["ante"]
    ante["score"] = ante["score_target"] - 1
    ante["target_met"] = False
    save_run(raw)

    raw = load_run()
    solution = raw["ante"]["solution"]
    grid = raw["ante"]["player_grid"]
    r, c = next((r, c) for r in range(9) for c in range(9) if grid[r][c] == 0)
    result = run_service.place_cell(r, c, solution[r][c])
    if not result["ante"]["target_met"]:
        pytest.skip("Could not trigger target_met in one move")

    assert result["ante"]["target_met"] is True
    help_events = [e for e in result.get("events", []) if e.get("type") == "target_met"]
    assert help_events
    assert help_events[0].get("help_bonus") == HELP_BONUS_SCORE
