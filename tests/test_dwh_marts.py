from __future__ import annotations

import pandas as pd
import psycopg
import pytest

from src.analysis.dwh_postgres import build
from src.common.config import GEN
from src.redash_sync.spec import load_dashboards, query_sql
from tests.helpers import render_params, viz_columns

DB = "dwh_check"


@pytest.fixture(scope="module")
def dwh(pg_dsn):
    counts = build(DB)
    with psycopg.connect(dbname=DB, **pg_dsn, autocommit=True) as conn:
        yield conn, counts


def test_bad_rows_split_into_rejected_and_quarantine(dwh):
    conn, counts = dwh
    raw = pd.read_csv(GEN.data_dir / "promo_orders.csv", dtype=str, keep_default_na=False)
    assert counts["promo_orders_rejected"] == raw.created_at.str.startswith("2026-13").sum()
    reasons = dict(conn.execute(
        "SELECT reason, count(*) FROM finance.promo_orders_quarantine GROUP BY reason").fetchall())
    assert reasons["missing_seller_id"] == (raw.seller_id == "").sum()
    assert reasons["non_positive_amount"] == raw.amount.str.startswith("-").sum()
    assert counts["promo_orders"] + counts["promo_orders_quarantine"] == counts["promo_orders_stg"]


def test_revenue_mart_matches_facts(dwh):
    conn, _ = dwh
    facts = conn.execute("SELECT sum(amount) FROM finance.promo_orders WHERE status = 'paid'").fetchone()[0]
    mart = conn.execute("SELECT sum(revenue) FROM finance.fct_promo_revenue_daily").fetchone()[0]
    assert facts == mart


def test_retention_month_zero_is_full_cohort(dwh):
    conn, _ = dwh
    rows = conn.execute("SELECT retention FROM finance.fct_seller_retention WHERE month_number = 0").fetchall()
    assert rows and all(abs(r[0] - 1.0) < 1e-9 for r in rows)
    later = conn.execute("SELECT max(retention) FROM finance.fct_seller_retention WHERE month_number > 0").fetchone()[0]
    assert 0 < later < 1


@pytest.mark.parametrize("spec_query", [
    (d, q) for d in load_dashboards() for q in d.queries if q["data_source"] == "vertica"
], ids=lambda x: x[1]["key"])
def test_vertica_dashboard_queries(dwh, spec_query):
    conn, _ = dwh
    dash, q = spec_query
    cur = conn.execute(render_params(query_sql(q), dash.parameters))
    cols = {d.name for d in cur.description}
    rows = cur.fetchall()
    assert rows, f"{q['name']}: пустой результат"
    assert viz_columns(q) <= cols
