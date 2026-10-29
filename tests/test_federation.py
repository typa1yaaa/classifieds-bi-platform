from __future__ import annotations

import pytest

from src.analysis import emulate_federation as fed


@pytest.fixture(scope="module")
def materialized(ch, pg_dsn):
    fed.setup(ch)
    return fed.materialize(ch)


def test_every_paid_order_is_evaluated(ch, materialized):
    paid = ch.query("SELECT count() FROM x_vertica_finance.promo_orders WHERE status = 'paid'").result_rows[0][0]
    assert materialized == paid


def test_cross_system_reconciliation_is_clean(ch, materialized):
    rows = ch.query(fed.trino_file("reconciliation.sql")[0], settings={"join_use_nulls": 1}).result_rows
    assert {name for name, _, _ in rows} == {
        "orders_without_listing", "order_seller_mismatch", "paid_promo_day_not_flagged", "promo_effect_revenue_diff"}
    assert all(v == 0 for _, _, v in rows), rows


def test_eligibility_rules(ch, materialized):
    share = ch.query("SELECT avg(is_eligible) FROM marts.promo_order_effect").result_rows[0][0]
    assert 0.1 < share < 0.6
    bad = ch.query("""
        SELECT count() FROM marts.promo_order_effect AS e
        INNER JOIN x_postgresql_public.listings AS l ON l.listing_id = e.listing_id
        WHERE e.is_eligible = 1 AND dateDiff('day', toDate(l.created_at), e.promo_start_date) < 14""").result_rows[0][0]
    assert bad == 0
