from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default)


@dataclass(frozen=True)
class GenConfig:
    seed: int = int(_env("SEED", "42"))
    start_date: date = date.fromisoformat(_env("START_DATE", "2026-04-01"))
    days: int = int(_env("DAYS", "180"))
    n_listings: int = int(_env("N_LISTINGS", "200000"))
    n_sellers: int = int(_env("N_SELLERS", "30000"))
    n_users: int = int(_env("N_USERS", "500000"))

    events_scale: float = float(_env("EVENTS_SCALE", "4.0"))
    data_dir: Path = Path(_env("DATA_DIR", str(ROOT / "data")))


    ios_release_date: date = date.fromisoformat(_env("IOS_RELEASE_DATE", "2026-09-10"))
    pipeline_incident_date: date = date.fromisoformat(_env("PIPELINE_INCIDENT_DATE", "2026-08-14"))

    @property
    def end_date(self) -> date:
        return self.start_date + timedelta(days=self.days - 1)

    @property
    def gen_dir(self) -> Path:
        return self.data_dir / "_gen"


@dataclass(frozen=True)
class Conn:
    pg_host: str = _env("PG_HOST", "localhost")
    pg_port: int = int(_env("PG_PORT", "5432"))
    pg_db: str = _env("PG_DB", "marketplace")
    pg_user: str = _env("PG_USER", "bi")
    pg_password: str = _env("PG_PASSWORD", "bi")

    pg_host_for_ch: str = _env("PG_HOST_FOR_CH", _env("PG_HOST", "localhost"))

    ch_host: str = _env("CH_HOST", "localhost")
    ch_port: int = int(_env("CH_PORT", "8123"))
    ch_user: str = _env("CH_USER", "bi")
    ch_password: str = _env("CH_PASSWORD", "bi")

    dwh_engine: str = _env("DWH_ENGINE", "postgres")
    dwh_pg_db: str = _env("DWH_PG_DB", "dwh")

    vertica_host: str = _env("VERTICA_HOST", "localhost")
    vertica_port: int = int(_env("VERTICA_PORT", "5433"))
    vertica_db: str = _env("VERTICA_DB", "VMart")
    vertica_user: str = _env("VERTICA_USER", "dbadmin")
    vertica_password: str = _env("VERTICA_PASSWORD", "")

    trino_host: str = _env("TRINO_HOST", "localhost")
    trino_port: int = int(_env("TRINO_PORT", "8080"))
    trino_user: str = _env("TRINO_USER", "bi")

    redash_url: str = _env("REDASH_URL", "http://localhost:5000")
    redash_api_key: str = _env("REDASH_API_KEY", "")


GEN = GenConfig()
CONN = Conn()
