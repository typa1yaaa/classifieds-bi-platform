from __future__ import annotations

import vertica_python

from src.common.config import CONN, GEN, ROOT
from src.common.sql import split_statements

DIMS = {
    "dim_category": ("categories", "category_id, parent_id, name, is_leaf"),
    "dim_region": ("regions", "region_id, name, federal_district, population_weight"),
    "dim_seller": ("sellers", "seller_id, seller_type, region_id, registered_at"),
    "dim_listing": ("listings", "listing_id, seller_id, category_id, region_id, price, created_at, closed_at, status"),
}
ORDER_COLS = "order_id, listing_id, seller_id, service_type, created_at, amount, status, active_from, active_to"


def connect():
    return vertica_python.connect(host=CONN.vertica_host, port=CONN.vertica_port, user=CONN.vertica_user,
                                  password=CONN.vertica_password, database=CONN.vertica_db, autocommit=True)


def run_file(cur, name: str) -> None:
    for stmt in split_statements((ROOT / "sql/vertica" / name).read_text()):
        cur.execute(stmt)
        if cur.description:
            cur.fetchall()
    print(f"vertica: {name} ok")


def copy_csv(cur, table: str, cols: str, path, rejected: str | None = None) -> None:
    tail = f" REJECTED DATA AS TABLE {rejected}" if rejected else " ABORT ON ERROR"
    sql = (f"COPY {table} ({cols}) FROM STDIN DELIMITER ',' ENCLOSED BY '\"' "
           f"NULL '' SKIP 1{tail}")
    with open(path, "rb") as f:
        cur.copy(sql, f)


def main() -> None:
    with connect() as conn:
        cur = conn.cursor()
        run_file(cur, "01_finance_schema.sql")
        for table, (csv, cols) in DIMS.items():
            copy_csv(cur, f"finance.{table}", cols, GEN.data_dir / f"{csv}.csv")
        copy_csv(cur, "finance.promo_orders_stg", ORDER_COLS, GEN.data_dir / "promo_orders.csv",
                 rejected="finance.promo_orders_rejected")
        run_file(cur, "02_validate_orders.sql")
        run_file(cur, "03_projections.sql")
        run_file(cur, "04_marts.sql")

        for t in ["promo_orders_stg", "promo_orders", "promo_orders_quarantine", "promo_orders_rejected",
                  "fct_promo_revenue_daily", "fct_seller_retention"]:
            cur.execute(f"SELECT COUNT(*) FROM finance.{t}")
            print(f"vertica finance.{t}: {cur.fetchone()[0]:,} rows")


if __name__ == "__main__":
    main()
