"""Tests for in-run boosts."""

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
        yield


def _start_ante(temp_db):
    run_service.new_run(seed=42)
    return run_service.start_from_map()


def test_target_met_does_not_end_ante(temp_db):
    _start_ante(temp_db)
    from app.db import load_run

    raw = load_run()
    ante = raw["ante"]
    ante["score"] = ante["score_target"]
    ante["target_met"] = False
    from app.game.run import _persist, _hydrate

    state = _hydrate(raw)
    state["ante"] = ante
    _persist(state)

    from app.db import load_run as lr
    data = lr()
    assert data["phase"] == "ante"


def test_fifty_fifty_requires_target(temp_db):
    _start_ante(temp_db)
    with pytest.raises(ValueError, match="Punkteziel"):
        run_service.buy_boost("fifty_fifty", 0, 0)
