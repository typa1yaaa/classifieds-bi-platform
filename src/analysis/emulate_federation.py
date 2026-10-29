from __future__ import annotations

import pandas as pd
import sqlglot

from src.common.config import CONN, GEN, ROOT
from src.common.sql import split_statements
from src.loaders.clickhouse import client, run_file
from src.loaders.trino import EFFECT_COLS

CATALOG_MAP = {
    "vertica.finance.": "x_vertica_finance.",
    "postgresql.public.": "x_postgresql_public.",
    "clickhouse.marts.": "marts.",
    "clickhouse.raw.": "raw.",
}


def valid_orders() -> pd.DataFrame:
    """Те же правила, что COPY REJECTED DATA + 02_validate_orders.sql."""
    df = pd.read_csv(GEN.data_dir / "promo_orders.csv", dtype=str, keep_default_na=False)
    for col in ["created_at", "active_from", "active_to"]:
        df[col] = pd.to_datetime(df[col].replace("", None), errors="coerce", format="%Y-%m-%d %H:%M:%S")
    rejected = df.created_at.isna()
    df = df[~rejected].copy()
    df["seller_id"] = pd.to_numeric(df.seller_id.replace("", None), errors="coerce")
    df["amount"] = pd.to_numeric(df.amount, errors="coerce")
    ok = (df.seller_id.notna() & (df.amount > 0) & df.status.isin(["paid", "cancelled", "refunded"])
          & df.service_type.isin(["bump", "highlight", "premium"]))
    out = df[ok].copy()
    out["order_id"] = out.order_id.astype(int)
    out["listing_id"] = out.listing_id.astype(int)
    out["seller_id"] = out.seller_id.astype(int)
    return out


def setup(ch) -> None:
    ch.command("DROP DATABASE IF EXISTS x_postgresql_public")
    ch.command(f"CREATE DATABASE x_postgresql_public ENGINE = PostgreSQL("
               f"'{CONN.pg_host_for_ch}:{CONN.pg_port}', '{CONN.pg_db}', '{CONN.pg_user}', "
               f"'{CONN.pg_password}', 'public')")
    ch.command("CREATE DATABASE IF NOT EXISTS x_vertica_finance")
    ch.command("DROP TABLE IF EXISTS x_vertica_finance.promo_orders")
    ch.command("""
        CREATE TABLE x_vertica_finance.promo_orders (
            order_id UInt32, listing_id UInt32, seller_id UInt32, service_type String,
            created_at DateTime, amount Decimal(12, 2), status String,
            active_from Nullable(DateTime), active_to Nullable(DateTime)
        ) ENGINE = MergeTree ORDER BY order_id""")
    orders = valid_orders()
    csv = orders[["order_id", "listing_id", "seller_id", "service_type", "created_at", "amount", "status",
                  "active_from", "active_to"]].to_csv(index=False, date_format="%Y-%m-%d %H:%M:%S")
    ch.raw_insert("x_vertica_finance.promo_orders", insert_block=csv.encode(), fmt="CSVWithNames")


def to_clickhouse(sql: str) -> str:
    for k, v in CATALOG_MAP.items():
        sql = sql.replace(k, v)
    return sqlglot.transpile(sql, read="trino", write="clickhouse")[0]


def trino_file(name: str) -> list[str]:
    return [to_clickhouse(s) for s in split_statements((ROOT / "sql/trino" / name).read_text())]


def materialize(ch) -> int:
    run_file(ch, "06_promo_effect.sql")
    ch.command("TRUNCATE TABLE marts.promo_order_effect")
    effect = trino_file("promo_order_effect.sql")[0]
    ch.command(f"INSERT INTO marts.promo_order_effect ({EFFECT_COLS}) SELECT {EFFECT_COLS} FROM ({effect})"
               f" SETTINGS join_use_nulls = 1")
    return ch.query("SELECT count() FROM marts.promo_order_effect").result_rows[0][0]


def main() -> None:
    ch = client()
    setup(ch)
    print(f"marts.promo_order_effect: {materialize(ch):,} rows (emulated federation)")
    rec = trino_file("reconciliation.sql")[0]
    for row in ch.query(rec, settings={"join_use_nulls": 1}).result_rows:
        print(row)


if __name__ == "__main__":
    main()
