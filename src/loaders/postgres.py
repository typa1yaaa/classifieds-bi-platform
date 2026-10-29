from __future__ import annotations

import psycopg

from src.common.config import CONN, GEN, ROOT

TABLES = ["categories", "regions", "sellers", "listings", "users"]


def connect() -> psycopg.Connection:
    return psycopg.connect(host=CONN.pg_host, port=CONN.pg_port, dbname=CONN.pg_db,
                           user=CONN.pg_user, password=CONN.pg_password, autocommit=True)


def main() -> None:
    with connect() as conn, conn.cursor() as cur:
        cur.execute((ROOT / "sql/postgres/schema.sql").read_text())
        for t in TABLES:
            path = GEN.data_dir / f"{t}.csv"
            with open(path, "rb") as f, cur.copy(f"COPY public.{t} FROM STDIN WITH (FORMAT csv, HEADER true)") as cp:
                while chunk := f.read(1 << 20):
                    cp.write(chunk)
            cur.execute(f"ANALYZE public.{t}")
            cur.execute(f"SELECT count(*) FROM public.{t}")
            print(f"postgres public.{t}: {cur.fetchone()[0]:,} rows")


if __name__ == "__main__":
    main()
