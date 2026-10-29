from __future__ import annotations

from dataclasses import replace

import pytest

from src.redash_sync import apply as apply_mod
from src.redash_sync import client as client_mod
from src.redash_sync import simulate_activity
from src.redash_sync.spec import load_dashboards
from tests import fake_redash


@pytest.fixture()
def fake(monkeypatch):
    srv, st, url = fake_redash.start(api_key="test-key")
    monkeypatch.setattr(client_mod, "CONN", replace(client_mod.CONN, redash_url=url, redash_api_key="test-key"))
    monkeypatch.delenv("REDASH_SIM_USER_KEYS", raising=False)
    yield st
    srv.shutdown()


def snapshot(st):
    return (len(st.data_sources), len(st.snippets), len(st.queries), len(st.vizs),
            len(st.dashboards), len(st.widgets), len(st.alerts))


def test_apply_is_complete_and_idempotent(fake):
    specs = load_dashboards()
    apply_mod.main()
    assert fake.errors == []
    first = snapshot(fake)

    assert len(fake.dashboards) == len(specs)
    assert len(fake.queries) == sum(len(d.queries) for d in specs)
    assert len(fake.widgets) == sum(len(d.widgets) for d in specs)
    assert len(fake.alerts) == sum(1 for d in specs for q in d.queries if "alert" in q)
    assert all(not d["is_draft"] for d in fake.dashboards.values())
    certified = [d for d in fake.dashboards.values() if "certified" in d["tags"]]
    assert len(certified) == len(specs) - 1  # устаревший отчёт не сертифицирован

    apply_mod.main()
    assert fake.errors == []
    assert snapshot(fake) == first, "повторный запуск не должен ничего дублировать"


def test_simulated_views_skip_deprecated(fake):
    apply_mod.main()
    fake.views.clear()
    simulate_activity.main(total_views=200)
    viewed = {fake.dashboards[i]["name"] for i in fake.views}
    legacy = [d.name for d in load_dashboards() if not d.simulate_views]
    assert legacy and not set(legacy) & viewed
