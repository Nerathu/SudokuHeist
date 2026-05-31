"""Trick and content loading."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

CONTENT_DIR = Path(__file__).parent / "content"


@lru_cache
def load_content() -> dict:
    with (CONTENT_DIR / "tricks.json").open(encoding="utf-8") as f:
        data = json.load(f)
    with (CONTENT_DIR / "boss_rules.json").open(encoding="utf-8") as f:
        data["boss_rules"] = json.load(f)["boss_rules"]
    return data


def all_tricks() -> list[dict]:
    return load_content()["tricks"]


def all_kniffs() -> list[dict]:
    return load_content()["kniffs"]


def trick_by_id(item_id: str) -> dict | None:
    for item in all_tricks() + all_kniffs():
        if item["id"] == item_id:
            return item
    return None


def random_quote(rng) -> str:
    quotes = load_content()["raccoon_quotes"]
    return rng.choice(quotes)


def meta_upgrades() -> list[dict]:
    return load_content()["meta_upgrades"]
