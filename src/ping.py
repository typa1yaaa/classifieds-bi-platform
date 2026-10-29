from __future__ import annotations

import requests

from src.common.config import CONN


def check(name: str, fn) -> bool:
    try:
        fn()
        print(f"[ok]   {name}")
        return True
    except Exception as e:  # noqa: BLE001
        print(f"[fail] {name}: {type(e).__name__}: {str(e).splitlines()[0][:120]}")
        return False


def pg():
    from src.loaders.postgres import connect
    with connect() as c:
        c.execute("SELECT 1")


def ch():
    from src.loaders.clickhouse import client
    client().query("SELECT 1")


def dwh():
    if CONN.dwh_engine == "vertica":
        from src.loaders.vertica import connect
        with connect() as c:
            c.cursor().execute("SELECT 1")
    else:
        from src.loaders.postgres import connect
        with connect() as c:
            c.execute("SELECT 1")


def trino_():
    from src.loaders.trino import connect
    cur = connect().cursor()
    cur.execute("SELECT 1")
    cur.fetchall()


def redash():
    r = requests.get(f"{CONN.redash_url}/ping", timeout=5)
    r.raise_for_status()


if __name__ == "__main__":
    results = [check("postgres", pg), check("clickhouse", ch), check(f"dwh ({CONN.dwh_engine})", dwh),
               check("trino", trino_), check("redash", redash)]
    print(f"{sum(results)}/{len(results)} systems reachable")
