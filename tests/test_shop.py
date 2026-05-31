"""Shop offer tests."""

import random

from app.game.shop import generate_shop_offers
from app.game.tricks import all_tricks


def test_shop_excludes_owned_tricks():
    owned = [all_tricks()[0]["id"], all_tricks()[1]["id"]]
    offers = generate_shop_offers(owned, random.Random(42))
    offered_ids = {t["id"] for t in offers["tricks"]}
    assert not offered_ids & set(owned)


def test_shop_no_duplicate_owned_when_few_left():
    owned = [t["id"] for t in all_tricks()]
    offers = generate_shop_offers(owned, random.Random(1))
    assert offers["tricks"] == []
