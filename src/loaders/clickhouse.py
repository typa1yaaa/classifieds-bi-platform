from __future__ import annotations

import os
import time
from datetime import timedelta

import clickhouse_connect

from src.common.config import CONN, GEN, ROOT
from src.common.sql import render, split_statements

CHUNK_DAYS = 30


def client():
    return clickhouse_connect.get_client(host=CONN.ch_host, port=CONN.ch_port, username=CONN.ch_user,
                                         password=CONN.ch_password, send_receive_timeout=3600,
                                         compress=os.environ.get("CH_COMPRESS", "1") == "1")


def run_file(ch, name: str, **params) -> None:
    for stmt in split_statements(render((ROOT / "sql/clickhouse" / name).read_text(), **params)):
        ch.command(stmt)


def insert_csv(ch, table: str, path) -> None:
    ch.raw_insert(table, insert_block=path.read_bytes(), fmt="CSVWithNames")


def load_gen_tables(ch) -> None:
    ch.command("DROP TABLE IF EXISTS gen.listings")
    ch.command("""
        CREATE TABLE gen.listings (
            listing_id UInt32, seller_id UInt32, category_id UInt16, parent_category_id UInt8,
            region_id UInt16, created_date Date, closed_date Date, popularity Float32,
            imp_factor Float32, base_ctr Float32, base_cr Float32
        ) ENGINE = MergeTree ORDER BY listing_id""")
    insert_csv(ch, "gen.listings", GEN.gen_dir / "listing_latent.csv")

    ch.command("DROP TABLE IF EXISTS gen.promo_days")
    ch.command("""
        CREATE TABLE gen.promo_days (
            listing_id UInt32, day Date, service_type LowCardinality(String),
            imp_mult Float32, ctr_mult Float32
        ) ENGINE = MergeTree ORDER BY (listing_id, day)""")
    insert_csv(ch, "gen.promo_days", GEN.gen_dir / "promo_days.csv")
    for t in ["gen.listings", "gen.promo_days"]:
        print(f"clickhouse {t}: {ch.query(f'SELECT count() FROM {t}').result_rows[0][0]:,} rows")


def generate_events(ch) -> None:
    sql = (ROOT / "sql/clickhouse/03_generate_events.sql").read_text()
    d = GEN.start_date
    while d <= GEN.end_date:
        d_to = min(d + timedelta(days=CHUNK_DAYS - 1), GEN.end_date)
        t0 = time.time()
        for stmt in split_statements(render(
                sql, d_from=d, d_to=d_to, start_date=GEN.start_date, days=GEN.days, n_users=GEN.n_users,
                scale=GEN.events_scale, ios_release_date=GEN.ios_release_date,
                incident_date=GEN.pipeline_incident_date)):
            ch.command(stmt)
        print(f"clickhouse events {d}..{d_to} in {time.time() - t0:.1f}s")
        d = d_to + timedelta(days=1)
    total = ch.query("SELECT count() FROM raw.events").result_rows[0][0]
    print(f"clickhouse raw.events: {total:,} rows")


def main() -> None:
    ch = client()
    run_file(ch, "00_databases.sql")
    run_file(ch, "01_raw_events.sql")
    run_file(ch, "02_materialized_views.sql")
    run_file(ch, "04_dictionaries.sql", pg_host=CONN.pg_host_for_ch, pg_port=CONN.pg_port, pg_db=CONN.pg_db,
             pg_user=CONN.pg_user, pg_password=CONN.pg_password)
    load_gen_tables(ch)
    generate_events(ch)


if __name__ == "__main__":
    main()
