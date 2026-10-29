from __future__ import annotations

import pytest

from src.common.config import GEN
from src.generator.orders import SERVICES


def scalar(ch, sql: str):
    return ch.query(sql).result_rows[0][0]


def test_staging_has_no_duplicates(ch):
    raw = scalar(ch, "SELECT count() FROM raw.events")
    raw_unique = scalar(ch, "SELECT uniqExact(event_id) FROM raw.events")
    stg = scalar(ch, "SELECT count() FROM staging.stg_events")
    assert raw > raw_unique, "в сырых данных должны быть повторные доставки"
    assert stg == raw_unique


def test_marts_reconcile_with_staging(ch):
    stg = ch.query("SELECT countIf(event_type='view'), countIf(event_type='contact') FROM staging.stg_events").result_rows[0]
    for table in ["marts.fct_listing_daily", "marts.fct_category_daily", "marts.fct_platform_daily"]:
        mart = ch.query(f"SELECT sum(views), sum(contacts) FROM {table}").result_rows[0]
        assert tuple(mart) == tuple(stg), table


def test_dq_catches_only_the_pipeline_incident(ch):
    fails = ch.query("SELECT check_name, check_date FROM dq.dq_checks_daily WHERE status = 'fail'").result_rows
    assert fails, "инцидент с потерей батча должен быть пойман"
    assert {d for _, d in fails} == {GEN.pipeline_incident_date}
    assert ("volume_vs_same_weekday", GEN.pipeline_incident_date) in fails


def test_ios_conversion_drop_is_business_not_data(ch):
    rel = GEN.ios_release_date
    rows = dict(ch.query(f"""
        SELECT platform,
               (sumIf(contacts, event_date >= '{rel}') / sumIf(views, event_date >= '{rel}'))
             / (sumIf(contacts, event_date <  '{rel}') / sumIf(views, event_date <  '{rel}'))
        FROM marts.fct_platform_daily
        WHERE event_date >= toDate('{rel}') - 28
        GROUP BY platform""").result_rows)
    assert rows["ios"] < 0.75
    assert 0.9 < rows["android"] < 1.1 and 0.9 < rows["web"] < 1.1
    vol = scalar(ch, f"""
        SELECT countIf(event_date >= '{rel}') / countIf(event_date >= toDate('{rel}') - 14 AND event_date < '{rel}')
        FROM staging.stg_events WHERE platform = 'ios' AND event_type = 'impression'""")
    assert vol > 0.8


@pytest.fixture(scope="module")
def effect(ch):
    if scalar(ch, "SELECT count() FROM system.tables WHERE database='marts' AND name='promo_order_effect'") == 0:
        pytest.skip("нет marts.promo_order_effect: выполните make federation")
    if scalar(ch, "SELECT count() FROM marts.promo_order_effect") == 0:
        pytest.skip("marts.promo_order_effect пуста")
    return {r[0]: r[1:] for r in ch.query("""
        SELECT service_type,
               sumIf(contacts_per_day_promo, is_eligible) / sumIf(contacts_per_day_before, is_eligible),
               countIf(is_eligible)
        FROM marts.promo_order_effect GROUP BY service_type""").result_rows}


def test_before_after_estimate_is_close_to_truth(effect):
    for service, (_, _, _, imp, ctr) in SERVICES.items():
        truth = imp * ctr * 0.92
        estimate, n = effect[service]
        assert n > 500
        assert abs(estimate / truth - 1) < 0.25, (service, estimate, truth)


def test_naive_estimate_is_inflated(ch, effect):
    naive = dict(ch.query("""
        SELECT promo_service,
               avg(contacts) / (SELECT avg(contacts) FROM marts.fct_listing_daily WHERE is_promoted = 0)
        FROM marts.fct_listing_daily WHERE is_promoted = 1 GROUP BY promo_service""").result_rows)
    for service in SERVICES:
        assert naive[service] > 1.4 * effect[service][0], service
