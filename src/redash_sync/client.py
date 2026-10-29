from __future__ import annotations

import time
from typing import Any

import requests

from src.common.config import CONN


class RedashError(RuntimeError):
    pass


class Redash:
    def __init__(self, url: str | None = None, api_key: str | None = None):
        self.url = (url or CONN.redash_url).rstrip("/")
        key = api_key or CONN.redash_api_key
        if not key:
            raise RedashError("REDASH_API_KEY не задан: возьмите ключ в профиле администратора Redash и положите в .env")
        self.s = requests.Session()
        self.s.headers.update({"Authorization": f"Key {key}"})

    def _req(self, method: str, path: str, **kw) -> Any:
        r = self.s.request(method, f"{self.url}/api/{path.lstrip('/')}", timeout=60, **kw)
        if r.status_code >= 400:
            raise RedashError(f"{method} {path} -> {r.status_code}: {r.text[:300]}")
        return r.json() if r.content else None

    def get(self, path: str, **params):
        return self._req("GET", path, params=params)

    def post(self, path: str, payload: dict):
        return self._req("POST", path, json=payload)

    def delete(self, path: str):
        return self._req("DELETE", path)

    def paged(self, path: str) -> list[dict]:
        out, page = [], 1
        while True:
            data = self.get(path, page=page, page_size=250)
            out.extend(data["results"])
            if page * 250 >= data["count"]:
                return out
            page += 1

    def data_sources(self) -> list[dict]:
        return self.get("data_sources")

    def queries(self) -> list[dict]:
        return self.paged("queries")

    def query(self, query_id: int) -> dict:
        return self.get(f"queries/{query_id}")

    def dashboards(self) -> list[dict]:
        return self.paged("dashboards")

    def dashboard(self, dash: dict) -> dict:
        try:
            return self.get(f"dashboards/{dash['id']}")
        except RedashError:
            return self.get(f"dashboards/{dash['slug']}")

    def refresh(self, query_id: int, parameters: dict | None = None, timeout: int = 300) -> bool:
        job = self.post(f"queries/{query_id}/results", {"parameters": parameters or {}, "max_age": 0})
        if "query_result" in job:
            return True
        job_id = job["job"]["id"]
        deadline = time.time() + timeout
        while time.time() < deadline:
            status = self.get(f"jobs/{job_id}")["job"]
            if status["status"] == 3:
                return True
            if status["status"] == 4:
                raise RedashError(f"query {query_id} failed: {status.get('error')}")
            time.sleep(1)
        raise RedashError(f"query {query_id}: timeout")
