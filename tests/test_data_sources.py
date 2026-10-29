from __future__ import annotations

from src.redash_sync.spec import load_data_sources


def dwh_source(monkeypatch, engine: str) -> dict:
    monkeypatch.setenv("DWH_ENGINE", engine)
    return next(d for d in load_data_sources() if d["key"] == "vertica")


def test_postgres_dwh_by_default(monkeypatch):
    ds = dwh_source(monkeypatch, "postgres")
    assert ds["type"] == "pg" and ds["options"]["dbname"] == "dwh"


def test_vertica_when_requested(monkeypatch):
    ds = dwh_source(monkeypatch, "vertica")
    assert ds["type"] == "vertica" and ds["options"]["port"] == 5433
