from __future__ import annotations

import io
import re
import sys

import pandas as pd
import psycopg

from src.common.config import CONN, GEN, ROOT
from src.common.sql import split_statements
from src.loaders.vertica import DIMS, ORDER_COLS

VERTICA_PHYSICAL = re.compile(
    r"\)\s*(ORDER BY [^;]*?)?\s*(SEGMENTED BY HASH\([^)]*\) ALL NODES|UNSEGMENTED ALL NODES)?\s*$", re.S)


def portable_ddl(stmt: str) -> str:
    if stmt.upper().startswith("CREATE TABLE"):
        return VERTICA_PHYSICAL.sub(")", stmt)
    return stmt


def connect(dbname: str):
    return psycopg.connect(host=CONN.pg_host, port=CONN.pg_port, user=CONN.pg_user, password=CONN.pg_password,
                           dbname=dbname, autocommit=True)


def ensure_db(dbname: str) -> None:
    with psycopg.connect(host=CONN.pg_host, port=CONN.pg_port, user=CONN.pg_user, password=CONN.pg_password,
                         dbname=CONN.pg_db, autocommit=True) as c:
        if not c.execute("SELECT 1 FROM pg_database WHERE datname = %s", (dbname,)).fetchone():
            c.execute(f'CREATE DATABASE "{dbname}"')


def copy_df(cur, table: str, df: pd.DataFrame) -> None:
    buf = io.StringIO()
    df.to_csv(buf, index=False, header=False)
    with cur.copy(f"COPY {table} ({', '.join(df.columns)}) FROM STDIN WITH (FORMAT csv)") as cp:
        cp.write(buf.getvalue())


def build(dbname: str | None = None) -> dict:
    dbname = dbname or CONN.dwh_pg_db
    ensure_db(dbname)
    with connect(dbname) as conn, conn.cursor() as cur:
        for stmt in split_statements((ROOT / "sql/vertica/01_finance_schema.sql").read_text()):
            cur.execute(portable_ddl(stmt))
        cur.execute("DROP TABLE IF EXISTS finance.promo_orders_rejected")
        cur.execute("CREATE TABLE finance.promo_orders_rejected (rejected_data text, rejected_reason text)")

        for table, (csv, cols) in DIMS.items():
            df = pd.read_csv(GEN.data_dir / f"{csv}.csv", dtype=str, keep_default_na=False)
            df = df[[c.strip() for c in cols.split(",")]].replace("", None)
            copy_df(cur, f"finance.{table}", df)

        raw = pd.read_csv(GEN.data_dir / "promo_orders.csv", dtype=str, keep_default_na=False)
        parsed = pd.to_datetime(raw.created_at, format="%Y-%m-%d %H:%M:%S", errors="coerce")
        rejected = raw[parsed.isna()]
        for _, r in rejected.iterrows():
            cur.execute("INSERT INTO finance.promo_orders_rejected VALUES (%s, %s)",
                        (",".join(r.values), "invalid timestamp"))
        stg = raw[parsed.notna()][[c.strip() for c in ORDER_COLS.split(",")]].replace("", None)
        copy_df(cur, "finance.promo_orders_stg", stg)

        for name in ["02_validate_orders.sql", "04_marts.sql"]:
            for stmt in split_statements((ROOT / "sql/vertica" / name).read_text()):
                cur.execute(stmt)

        counts = {}
        for t in ["promo_orders_stg", "promo_orders", "promo_orders_quarantine", "promo_orders_rejected",
                  "fct_promo_revenue_daily", "fct_seller_month", "fct_seller_retention"]:
            counts[t] = cur.execute(f"SELECT count(*) FROM finance.{t}").fetchone()[0]
        return counts


if __name__ == "__main__":
    for t, n in build(*(sys.argv[1:] or [])).items():
        print(f"{t:<28} {n:>10,}")
