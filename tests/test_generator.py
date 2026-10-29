from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from src.common.config import GEN
from src.generator.orders import SERVICES, add_dirty_rows, build_orders
from src.generator.reference import build_all

SMALL = replace(GEN, n_listings=6000, n_sellers=1500, n_users=5000, days=60)


@pytest.fixture(scope="module")
def ref():
    return build_all(SMALL)


@pytest.fixture(scope="module")
def orders(ref):
    return build_orders(SMALL, ref["listing_latent"], ref["seller_latent"])


def test_reproducible(ref):
    again = build_all(SMALL)
    assert ref["listings"].equals(again["listings"])
    assert ref["listing_latent"].popularity.equals(again["listing_latent"].popularity)


def test_reference_integrity(ref):
    listings, sellers, cats = ref["listings"], ref["sellers"], ref["categories"]
    assert listings.listing_id.is_unique
    assert set(listings.seller_id) <= set(sellers.seller_id)
    leaf_ids = set(cats[cats.is_leaf == "true"].category_id)
    assert set(listings.category_id) <= leaf_ids
    assert (listings.closed_at.isna() == (listings.status == "active")).all()


def test_selection_effect_is_built_in(ref, orders):
    o, _ = orders
    lat = ref["listing_latent"].set_index("listing_id")
    promoted_pop = lat.loc[o.listing_id.unique(), "popularity"].median()
    assert promoted_pop > 1.5 * lat.popularity.median()


def test_promo_days_follow_orders(orders):
    o, pdays = orders
    active = o[o.status.isin(["paid", "refunded"])]
    assert set(pdays.listing_id) == set(active.listing_id)
    assert set(pdays.service_type) <= set(SERVICES)
    assert pdays.duplicated(["listing_id", "day"]).sum() == 0
    assert o[o.status == "cancelled"].active_from.isna().all()


def test_dirty_rows(orders):
    o, _ = orders
    raw = add_dirty_rows(o, SMALL)
    extra = len(raw) - len(o)
    assert extra >= 3
    assert raw.order_id.is_unique
    bad = raw[raw.order_id > o.order_id.max()]
    kinds = {
        "negative": bad.amount.str.startswith("-").sum(),
        "no_seller": (bad.seller_id == "").sum(),
        "bad_date": bad.created_at.str.startswith("2026-13").sum(),
    }
    assert sum(kinds.values()) == extra
    assert np.all(np.array(list(kinds.values())) > 0)
