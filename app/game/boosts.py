"""In-run boosts bought with ante score after target is met."""

from __future__ import annotations

import random

BOOSTS = [
    {
        "id": "fifty_fifty",
        "name": "50/50",
        "description": "Zwei Kandidaten diagonal in der Zelle — antippen zum Setzen.",
        "cost": 28,
    },
    {
        "id": "reveal",
        "name": "Einblick",
        "description": "Eine Zelle wird korrekt aufgedeckt (ohne Zug).",
        "cost": 38,
    },
    {
        "id": "extra_moves",
        "name": "+5 Züge",
        "description": "Der Tresor bleibt länger offen.",
        "cost": 32,
    },
]


def boost_by_id(boost_id: str) -> dict | None:
    return next((b for b in BOOSTS if b["id"] == boost_id), None)


def can_afford_boost(ante: dict, cost: int) -> bool:
    if not ante.get("target_met"):
        return False
    floor = ante["score_target"]
    return ante["score"] - cost >= floor


def spend_score(ante: dict, cost: int) -> None:
    if not can_afford_boost(ante, cost):
        raise ValueError("Nicht genug Punkte (Minimum ist das gesicherte Ziel)")
    ante["score"] -= cost


def fifty_fifty_options(solution_val: int, rng: random.Random) -> tuple[int, int]:
    """Return (bottom_left, top_right) — one value is correct."""
    wrong = rng.choice([n for n in range(1, 10) if n != solution_val])
    correct = solution_val
    if rng.random() < 0.5:
        return wrong, correct
    return correct, wrong
