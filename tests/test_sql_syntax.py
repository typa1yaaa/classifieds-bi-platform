from __future__ import annotations

import pytest
import sqlglot

from src.analysis.dwh_postgres import portable_ddl
from src.common.config import ROOT
from src.common.sql import split_statements
from src.redash_sync.spec import load_dashboards, query_sql

TRINO_FILES = sorted((ROOT / "sql/trino").glob("*.sql"))
TRINO_REDASH = [q for d in load_dashboards() for q in d.queries if q["data_source"] == "trino"]


def statements(path):
    return split_statements(path.read_text())


@pytest.mark.parametrize("path", TRINO_FILES, ids=lambda p: p.name)
def test_trino_files_parse(path):
    for stmt in statements(path):
        body = stmt[len("EXPLAIN"):] if stmt.upper().startswith("EXPLAIN") else stmt
        sqlglot.parse_one(body, read="trino")


@pytest.mark.parametrize("q", TRINO_REDASH, ids=lambda q: q["key"])
def test_trino_dashboard_queries_parse(q):
    sqlglot.parse_one(split_statements(query_sql(q))[0], read="trino")


@pytest.mark.parametrize("name", ["01_finance_schema.sql", "02_validate_orders.sql", "04_marts.sql"])
def test_vertica_sql_parses(name):
    for stmt in statements(ROOT / "sql/vertica" / name):
        sqlglot.parse_one(portable_ddl(stmt), read="postgres")


def test_vertica_physical_clauses_are_stripped_only_from_tables():
    ddl = "CREATE TABLE t (a INT)\nORDER BY a\nSEGMENTED BY HASH(a) ALL NODES"
    assert portable_ddl(ddl) == "CREATE TABLE t (a INT)"
    assert portable_ddl("CREATE TABLE d (a INT)\nUNSEGMENTED ALL NODES") == "CREATE TABLE d (a INT)"
