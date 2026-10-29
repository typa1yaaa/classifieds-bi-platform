from __future__ import annotations

import sys
import time

import trino

from src.common.config import CONN, ROOT
from src.common.sql import split_statements
from src.loaders.clickhouse import client as ch_client
from src.loaders.clickhouse import run_file as ch_run_file

EFFECT_COLS = ("order_id, listing_id, seller_id, category_id, parent_category_id, region_id, service_type, "
               "amount, promo_start_date, promo_days, contacts_promo, contacts_before, impressions_promo, "
               "impressions_before, contacts_per_day_promo, contacts_per_day_before, extra_contacts, is_eligible")


def connect():
    return trino.dbapi.connect(host=CONN.trino_host, port=CONN.trino_port, user=CONN.trino_user)


def read(name: str) -> str:
    return split_statements((ROOT / "sql/trino" / name).read_text())[0]


def materialize_promo_effect() -> None:
    ch = ch_client()
    ch_run_file(ch, "06_promo_effect.sql")
    ch.command("TRUNCATE TABLE marts.promo_order_effect")

    t0 = time.time()
    cur = connect().cursor()
    cur.execute(f"INSERT INTO clickhouse.marts.promo_order_effect ({EFFECT_COLS})\n"
                f"SELECT {EFFECT_COLS} FROM (\n{read('promo_order_effect.sql')}\n)")
    cur.fetchall()
    n = ch.query("SELECT count() FROM marts.promo_order_effect").result_rows[0][0]
    print(f"trino -> clickhouse marts.promo_order_effect: {n:,} rows in {time.time() - t0:.1f}s")


def reconcile() -> None:
    cur = connect().cursor()
    cur.execute(read("reconciliation.sql"))
    for check, systems, violations in cur.fetchall():
        status = "ok  " if violations == 0 else "FAIL"
        print(f"[{status}] {check:<30} {systems:<22} violations={violations}")


def explain() -> None:
    out = ROOT / "docs/explain"
    out.mkdir(parents=True, exist_ok=True)
    cur = connect().cursor()
    for name in ["explain_pushdown.sql"]:
        for i, stmt in enumerate(split_statements((ROOT / "sql/trino" / name).read_text())):
            cur.execute(stmt)
            plan = "\n".join(r[0] for r in cur.fetchall())
            path = out / f"{name.removesuffix('.sql')}_{i + 1}.txt"
            path.write_text(stmt + "\n\n" + plan)
            print(f"saved {path.relative_to(ROOT)}")


if __name__ == "__main__":
    if sys.argv[1:] == ["explain"]:
        explain()
    else:
        materialize_promo_effect()
        reconcile()
