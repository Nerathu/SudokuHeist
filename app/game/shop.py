"""Shop offer generation."""

from __future__ import annotations

import random

from app.game.tricks import all_kniffs, all_tricks


REROLL_BASE_COST = 3


def reroll_cost(meta_shop_reroll_level: int) -> int:
    return max(1, REROLL_BASE_COST - meta_shop_reroll_level)


def generate_shop_offers(owned_trick_ids: list[str], rng: random.Random) -> dict:
    owned = set(owned_trick_ids)
    available_tricks = [t for t in all_tricks() if t["id"] not in owned]
    rng.shuffle(available_tricks)
    trick_offers = available_tricks[:4]

    kniff_offers = rng.sample(all_kniffs(), k=min(2, len(all_kniffs())))
    return {"tricks": trick_offers, "kniffs": kniff_offers}


def generate_shop_offers_with_meta(owned_trick_ids: list[str], rng: random.Random, meta_shop_reroll_level: int) -> dict:
    offers = generate_shop_offers(owned_trick_ids, rng)
    offers["reroll_cost"] = reroll_cost(meta_shop_reroll_level)
    return offers
