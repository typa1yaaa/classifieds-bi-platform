from __future__ import annotations

import pytest


@pytest.fixture(scope="session")
def ch():
    from src.loaders.clickhouse import client
    try:
        c = client()
        c.query("SELECT 1")
    except Exception as e:  # noqa: BLE001
        pytest.skip(f"ClickHouse недоступен: {e}")
    if c.query("SELECT count() FROM system.tables WHERE database = 'raw' AND name = 'events'").result_rows[0][0] == 0:
        pytest.skip("ClickHouse пуст: сначала make seed clickhouse dbt")
    return c


@pytest.fixture(scope="session")
def pg_dsn():
    import psycopg

    from src.common.config import CONN
    dsn = dict(host=CONN.pg_host, port=CONN.pg_port, user=CONN.pg_user, password=CONN.pg_password)
    try:
        with psycopg.connect(dbname=CONN.pg_db, **dsn, autocommit=True):
            pass
    except Exception as e:  # noqa: BLE001
        pytest.skip(f"PostgreSQL недоступен: {e}")
    return dsn
