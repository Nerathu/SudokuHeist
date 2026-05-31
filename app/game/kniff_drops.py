"""Random kniff drops on correct cell placements."""

from __future__ import annotations

from app.game.balance import (
    KNIFF_DROP_CHANCE,
    KNIFF_DROP_LUCK_MULT,
    KNIFF_DROP_MAX_PER_ANTE,
    KNIFF_MAX_STACK,
)
from app.game.tricks import all_kniffs, trick_by_id

_DROP_WEIGHTS = {
    "beute_boost": 35,
    "radiergummi": 30,
    "schummel_zettel": 25,
    "herz_pflaster": 10,
}


def try_kniff_drop(*, state: dict, ante: dict, events: list[dict]) -> bool:
    """Maybe grant a consumable kniff. Returns True if a drop occurred."""
    drops = ante.get("kniff_drops_this_ante", 0)
    if drops >= KNIFF_DROP_MAX_PER_ANTE:
        return False

    chance = KNIFF_DROP_CHANCE
    if "raccoon_luck" in state["trick_ids"]:
        chance = min(0.2, chance * KNIFF_DROP_LUCK_MULT)
    if state["rng"].random() >= chance:
        return False

    pool: list[dict] = []
    weights: list[int] = []
    for kniff in all_kniffs():
        kid = kniff["id"]
        if state["kniffs"].get(kid, 0) >= KNIFF_MAX_STACK:
            continue
        if kid == "herz_pflaster" and state["hearts"] >= state["max_hearts"]:
            continue
        pool.append(kniff)
        weights.append(_DROP_WEIGHTS.get(kid, 10))

    if not pool:
        return False

    chosen = state["rng"].choices(pool, weights=weights, k=1)[0]
    kid = chosen["id"]
    state["kniffs"][kid] = state["kniffs"].get(kid, 0) + 1
    ante["kniff_drops_this_ante"] = drops + 1
    events.append({
        "type": "kniff_drop",
        "kniff_id": kid,
        "name": chosen["name"],
        "message": f"Kniff gefunden: {chosen['name']}!",
    })
    return True


def kniff_label(kniff_id: str) -> str:
    item = trick_by_id(kniff_id)
    return item["name"] if item else kniff_id
