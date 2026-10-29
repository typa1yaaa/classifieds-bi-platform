from __future__ import annotations

import pytest

from src.redash_sync.spec import load_dashboards, query_sql, validate
from tests.helpers import render_params, viz_columns

CH_QUERIES = [(d, q) for d in load_dashboards() for q in d.queries if q["data_source"] == "clickhouse"]


def test_specs_are_consistent():
    assert validate(load_dashboards()) == []


@pytest.mark.parametrize("spec_query", CH_QUERIES, ids=lambda x: x[1]["key"])
def test_clickhouse_dashboard_query(ch, spec_query):
    dash, q = spec_query
    sql = render_params(query_sql(q), dash.parameters)
    if "promo_order_effect" in sql and ch.query(
            "SELECT count() FROM system.tables WHERE database='marts' AND name='promo_order_effect'").result_rows[0][0] == 0:
        pytest.skip("нет marts.promo_order_effect: выполните make federation")
    r = ch.query(sql)
    if q["key"] != "legacy":
        assert r.result_rows, f"{q['name']}: пустой результат"
    assert viz_columns(q) <= set(r.column_names)
