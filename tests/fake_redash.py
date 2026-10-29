from __future__ import annotations

import itertools
import json
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

VIZ_TYPES = {"TABLE", "CHART", "COUNTER"}
PARAM_TYPES = {"date-range", "enum", "query", "text", "number"}


class State:
    def __init__(self):
        self.ids = itertools.count(1)
        self.data_sources: dict[int, dict] = {}
        self.snippets: dict[int, dict] = {}
        self.queries: dict[int, dict] = {}
        self.vizs: dict[int, dict] = {}
        self.dashboards: dict[int, dict] = {}
        self.widgets: dict[int, dict] = {}
        self.alerts: dict[int, dict] = {}
        self.views: list[int] = []
        self.errors: list[str] = []

    def new_id(self) -> int:
        return next(self.ids)


def make_handler(st: State, api_key: str):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _send(self, code, obj=None):
            body = json.dumps(obj).encode() if obj is not None else b""
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _body(self):
            n = int(self.headers.get("Content-Length") or 0)
            return json.loads(self.rfile.read(n)) if n else {}

        def _auth(self):
            if self.headers.get("Authorization") != f"Key {api_key}":
                self._send(403, {"message": "bad key"})
                return False
            return True

        def _err(self, msg):
            st.errors.append(msg)
            self._send(400, {"message": msg})

        def do_GET(self):
            if not self._auth():
                return
            path = self.path.split("?")[0]
            if path == "/api/data_sources":
                return self._send(200, list(st.data_sources.values()))
            if path == "/api/query_snippets":
                return self._send(200, list(st.snippets.values()))
            if path == "/api/alerts":
                return self._send(200, list(st.alerts.values()))
            if path == "/api/queries":
                res = list(st.queries.values())
                return self._send(200, {"count": len(res), "results": res})
            if path == "/api/dashboards":
                res = list(st.dashboards.values())
                return self._send(200, {"count": len(res), "results": res})
            if m := re.fullmatch(r"/api/queries/(\d+)", path):
                q = dict(st.queries[int(m[1])])
                q["visualizations"] = [v for v in st.vizs.values() if v["query_id"] == q["id"]]
                return self._send(200, q)
            if m := re.fullmatch(r"/api/dashboards/(\d+)", path):
                d = dict(st.dashboards[int(m[1])])
                d["widgets"] = [w for w in st.widgets.values() if w["dashboard_id"] == d["id"]]
                st.views.append(d["id"])
                return self._send(200, d)
            if re.fullmatch(r"/api/jobs/[\w-]+", path):
                return self._send(200, {"job": {"status": 3}})
            self._send(404, {"message": path})

        def do_DELETE(self):
            if not self._auth():
                return
            if m := re.fullmatch(r"/api/widgets/(\d+)", self.path):
                st.widgets.pop(int(m[1]))
                return self._send(200, {})
            self._send(404, {})

        def do_POST(self):
            if not self._auth():
                return
            p, b = self.path, self._body()
            if p == "/api/data_sources":
                if not {"name", "type", "options"} <= b.keys():
                    return self._err("data source fields")
                i = st.new_id(); st.data_sources[i] = {**b, "id": i}
                return self._send(200, st.data_sources[i])
            if m := re.fullmatch(r"/api/data_sources/(\d+)", p):
                st.data_sources[int(m[1])].update(b); return self._send(200, st.data_sources[int(m[1])])
            if p == "/api/query_snippets":
                i = st.new_id(); st.snippets[i] = {**b, "id": i}; return self._send(200, st.snippets[i])
            if m := re.fullmatch(r"/api/query_snippets/(\d+)", p):
                st.snippets[int(m[1])].update(b); return self._send(200, {})
            if p == "/api/queries":
                if not {"name", "query", "data_source_id"} <= b.keys() or b["data_source_id"] not in st.data_sources:
                    return self._err("query fields")
                if not self._check_params(b):
                    return
                i = st.new_id()
                st.queries[i] = {**b, "id": i, "is_draft": True, "tags": []}
                v = st.new_id()
                st.vizs[v] = {"id": v, "query_id": i, "name": "Table", "type": "TABLE", "options": {}}
                return self._send(200, st.queries[i])
            if m := re.fullmatch(r"/api/queries/(\d+)/results", p):
                return self._send(200, {"job": {"id": "job-1"}})
            if m := re.fullmatch(r"/api/queries/(\d+)", p):
                if "options" in b and not self._check_params(b):
                    return
                st.queries[int(m[1])].update(b); return self._send(200, st.queries[int(m[1])])
            if p == "/api/visualizations":
                if b.get("type") not in VIZ_TYPES or b.get("query_id") not in st.queries:
                    return self._err(f"viz {b.get('type')}")
                i = st.new_id(); st.vizs[i] = {**b, "id": i}; return self._send(200, st.vizs[i])
            if m := re.fullmatch(r"/api/visualizations/(\d+)", p):
                st.vizs[int(m[1])].update(b); return self._send(200, st.vizs[int(m[1])])
            if p == "/api/dashboards":
                i = st.new_id()
                st.dashboards[i] = {"id": i, "name": b["name"], "slug": f"d-{i}", "tags": [], "is_draft": True}
                return self._send(200, st.dashboards[i])
            if m := re.fullmatch(r"/api/dashboards/(\d+)", p):
                st.dashboards[int(m[1])].update(b); return self._send(200, st.dashboards[int(m[1])])
            if p == "/api/widgets":
                pos = b.get("options", {}).get("position", {})
                if b.get("dashboard_id") not in st.dashboards or not {"col", "row", "sizeX", "sizeY"} <= pos.keys():
                    return self._err("widget fields")
                if b.get("visualization_id") is not None and b["visualization_id"] not in st.vizs:
                    return self._err("widget viz")
                i = st.new_id(); st.widgets[i] = {**b, "id": i}; return self._send(200, st.widgets[i])
            if p == "/api/alerts":
                if b.get("query_id") not in st.queries or "column" not in b.get("options", {}):
                    return self._err("alert fields")
                i = st.new_id(); st.alerts[i] = {**b, "id": i}; return self._send(200, st.alerts[i])
            if m := re.fullmatch(r"/api/alerts/(\d+)", p):
                st.alerts[int(m[1])].update(b); return self._send(200, {})
            self._send(404, {"message": p})

        def _check_params(self, b) -> bool:
            for prm in b.get("options", {}).get("parameters", []):
                if prm.get("type") not in PARAM_TYPES:
                    self._err(f"param type {prm.get('type')}"); return False
                if prm["type"] == "query" and prm.get("queryId") not in st.queries:
                    self._err("param queryId"); return False
                if prm["type"] == "enum" and not prm.get("enumOptions"):
                    self._err("param enumOptions"); return False
            return True

    return H


def start(api_key: str = "test-key"):
    st = State()
    srv = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(st, api_key))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, st, f"http://127.0.0.1:{srv.server_address[1]}"
