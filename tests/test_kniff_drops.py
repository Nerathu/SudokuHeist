"""Kniff drop tests."""

import os
import tempfile

import pytest

from app.db import init_db, load_run, save_meta
from app.game import run as run_service
from app.game.balance import KNIFF_DROP_MAX_PER_ANTE, KNIFF_MAX_STACK
from app.game.kniff_drops import try_kniff_drop


@pytest.fixture
def temp_db(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "test.db")
        monkeypatch.setenv("DB_PATH", db_path)
        init_db()
        save_meta({"meta_beute": 0, "upgrades": {}})
        yield db_path


def test_try_kniff_drop_respects_cap(temp_db):
    run_service.new_run(seed=99)
    run_service.start_from_map()
    raw = load_run()
    state = run_service._hydrate(raw)
    ante = state["ante"]
    ante["kniff_drops_this_ante"] = KNIFF_DROP_MAX_PER_ANTE
    events: list[dict] = []
    assert try_kniff_drop(state=state, ante=ante, events=events) is False


def test_try_kniff_drop_grants_item(temp_db, monkeypatch):
    monkeypatch.setattr("app.game.kniff_drops.KNIFF_DROP_CHANCE", 1.0)
    run_service.new_run(seed=123)
    run_service.start_from_map()
    raw = load_run()
    state = run_service._hydrate(raw)
    ante = state["ante"]
    events: list[dict] = []
    assert try_kniff_drop(state=state, ante=ante, events=events) is True
    assert any(e["type"] == "kniff_drop" for e in events)
    assert sum(state["kniffs"].values()) == 1
    assert ante["kniff_drops_this_ante"] == 1


def test_kniff_drop_on_correct_placement(temp_db, monkeypatch):
    monkeypatch.setattr("app.game.kniff_drops.KNIFF_DROP_CHANCE", 1.0)
    run_service.new_run(seed=456)
    state = run_service.start_from_map()
    grid = state["ante"]["player_grid"]
    raw = load_run()
    solution = raw["ante"]["solution"]
    r, c = next((ri, ci) for ri in range(9) for ci in range(9) if grid[ri][ci] == 0)
    result = run_service.place_cell(r, c, solution[r][c])
    assert any(e["type"] == "kniff_drop" for e in result.get("events", []))
    assert sum(result["kniffs"].values()) >= 1


def test_kniff_stack_cap(temp_db, monkeypatch):
    monkeypatch.setattr("app.game.kniff_drops.KNIFF_DROP_CHANCE", 1.0)
    run_service.new_run(seed=789)
    run_service.start_from_map()
    raw = load_run()
    state = run_service._hydrate(raw)
    state["kniffs"] = {"beute_boost": KNIFF_MAX_STACK}
    ante = state["ante"]
    events: list[dict] = []
    assert try_kniff_drop(state=state, ante=ante, events=events) is True
    assert state["kniffs"]["beute_boost"] == KNIFF_MAX_STACK
    assert events[0]["kniff_id"] != "beute_boost"
