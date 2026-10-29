from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from string import Template

from src.common.config import ROOT

REDASH_DIR = ROOT / "redash"

ENV_DEFAULTS = {
    "REDASH_SOURCE_CH_HOST": "clickhouse", "REDASH_SOURCE_VERTICA_HOST": "vertica",
    "REDASH_SOURCE_TRINO_HOST": "trino", "REDASH_SOURCE_PG_HOST": "postgres",
    "CH_USER": "bi", "CH_PASSWORD": "bi", "VERTICA_USER": "dbadmin", "VERTICA_PASSWORD": "",
    "VERTICA_DB": "VMart", "PG_USER": "bi", "PG_PASSWORD": "bi", "DWH_PG_DB": "dwh",
}


@dataclass
class DashboardSpec:
    file: Path
    name: str
    tags: list[str]
    parameters: dict
    queries: list[dict]
    widgets: list[dict]
    simulate_views: bool
    raw: dict


def load_dashboards() -> list[DashboardSpec]:
    out = []
    for f in sorted((REDASH_DIR / "dashboards").glob("*.json")):
        d = json.loads(f.read_text())
        out.append(DashboardSpec(f, d["name"], d.get("tags", []), d.get("parameters", {}), d["queries"],
                                 d["widgets"], d.get("simulate_views", True), d))
    return out


def load_data_sources() -> list[dict]:
    env = {**ENV_DEFAULTS, **os.environ}
    text = Template((REDASH_DIR / "data_sources.json").read_text()).safe_substitute(env)
    sources = json.loads(text)
    if env.get("DWH_ENGINE", "postgres") != "vertica":
        for ds in sources:
            if ds["key"] == "vertica":
                ds.update(name="PostgreSQL | финансовое DWH", type="pg", options={
                    "host": env["REDASH_SOURCE_PG_HOST"], "port": 5432, "user": env["PG_USER"],
                    "password": env["PG_PASSWORD"], "dbname": env["DWH_PG_DB"]})
    return sources


def load_snippets() -> list[dict]:
    return json.loads((REDASH_DIR / "snippets.json").read_text())


def query_sql(q: dict) -> str:
    return (REDASH_DIR / "queries" / q["file"]).read_text()


def sql_params(sql: str) -> set[str]:
    return {m.split(".")[0] for m in re.findall(r"\{\{\s*([\w.]+)\s*\}\}", sql)}


def validate(dashboards: list[DashboardSpec]) -> list[str]:
    errors = []
    names = set()
    for d in dashboards:
        keys = {q["key"]: q for q in d.queries}
        for q in d.queries:
            if q["name"] in names:
                errors.append(f"{d.file.name}: дублируется имя запроса «{q['name']}»")
            names.add(q["name"])
            path = REDASH_DIR / "queries" / q["file"]
            if not path.exists():
                errors.append(f"{d.file.name}: нет файла {q['file']}")
                continue
            used = sql_params(path.read_text())
            declared = set(q.get("params", []))
            if used != declared:
                errors.append(f"{d.file.name}: {q['key']} параметры в SQL {sorted(used)} != объявленные {sorted(declared)}")
            for p in declared:
                if p not in d.parameters:
                    errors.append(f"{d.file.name}: {q['key']} использует неописанный параметр {p}")
                elif d.parameters[p]["type"] == "query" and d.parameters[p]["query"] not in keys:
                    errors.append(f"{d.file.name}: параметр {p} ссылается на неизвестный запрос")
        for w in d.widgets:
            if "viz" in w:
                qk, vk = w["viz"].split(".")
                vizs = {v["key"] for v in keys.get(qk, {}).get("visualizations", [])}
                if vk not in vizs:
                    errors.append(f"{d.file.name}: виджет ссылается на несуществующую визуализацию {w['viz']}")
            col, row, sx, sy = w["pos"]
            if col + sx > 6:
                errors.append(f"{d.file.name}: виджет {w.get('viz', 'text')} выходит за 6 колонок сетки")
    return errors


def build_parameter(name: str, p: dict, query_ids: dict[str, int]) -> dict:
    out = {"name": name, "title": p.get("title", name), "type": p["type"], "value": p.get("value"),
           "global": False, "locals": []}
    if p["type"] == "enum":
        out["enumOptions"] = "\n".join(p["options"])
    if p["type"] == "query":
        out["queryId"] = query_ids[p["query"]]
    if p.get("multi"):
        q = p.get("quote", "'")
        out["multiValuesOptions"] = {"prefix": q, "suffix": q, "separator": ","}
    return out


def render_default_params(sql: str, params: dict) -> str:
    def value(name: str, attr: str | None) -> str:
        p = params[name]
        v = p["value"]
        if p["type"] == "date-range":
            return v[attr]
        if p.get("multi"):
            q = p.get("quote", "'")
            return ",".join(f"{q}{x}{q}" for x in v)
        return str(v)

    return re.sub(r"\{\{\s*(\w+)(?:\.(\w+))?\s*\}\}", lambda m: value(m.group(1), m.group(2)), sql)


def default_parameter_values(names: list[str], params: dict) -> dict:
    return {n: params[n]["value"] for n in names}


def viz_type(v: dict) -> str:
    return {"counter": "COUNTER", "chart": "CHART", "table": "TABLE"}[v["type"]]


def viz_options(v: dict) -> dict:
    if v["type"] == "table":
        opts = {"itemsPerPage": 25}
        if v.get("titles"):
            opts["columns"] = [{"name": c, "title": t, "visible": True, "order": i}
                               for i, (c, t) in enumerate(v["titles"].items())]
        return opts
    if v["type"] == "counter":
        opts = {"counterLabel": v["name"], "counterColName": v["value"], "rowNumber": 1,
                "targetRowNumber": 1, "stringDecimal": v.get("decimals", 0),
                "stringDecChar": ",", "stringThouSep": " ", "stringPrefix": v.get("prefix", ""),
                "stringSuffix": v.get("suffix", ""), "formatTargetValue": True, "tooltipFormat": "0,0.000"}
        if v.get("target"):
            opts["targetColName"] = v["target"]
        return opts

    kind = v["chart"]
    labels = v.get("labels", {})
    mapping = {v["x"]: "x"}
    for y in v.get("y", []):
        mapping[y] = "y"
    if v.get("series"):
        mapping[v["series"]] = "series"
    series_options = {y: {"yAxis": 0, "type": kind, "zIndex": i, "index": 0, **({"name": labels[y]} if y in labels else {})}
                      for i, y in enumerate(v.get("y", []))}
    return {
        "globalSeriesType": kind,
        "columnMapping": mapping,
        "seriesOptions": series_options,
        "valuesOptions": {},
        "xAxis": {"type": v.get("x_type", "-"), "labels": {"enabled": True}, "title": {"text": v.get("x_title", "")}},
        "yAxis": [{"type": "linear", "title": {"text": v.get("y_title", "")}},
                  {"type": "linear", "opposite": True, "title": {"text": ""}}],
        "series": {"stacking": v.get("stacking"), "error_y": {"type": "data", "visible": True}},
        "legend": {"enabled": v.get("legend", True), "placement": "auto", "traceorder": "normal"},
        "swappedAxes": bool(v.get("horizontal")),
        "sortX": v.get("sort_x", True),
        "missingValuesAsZero": True,
        "showDataLabels": False,
        "numberFormat": v.get("y_format", "0,0[.]00"),
        "percentFormat": "0[.]0%",
        "textFormat": "",
        "dateTimeFormat": "DD.MM.YY",
    }


def widget_options(w: dict, param_names: list[str]) -> dict:
    col, row, sx, sy = w["pos"]
    return {
        "isHidden": False,
        "position": {"col": col, "row": row, "sizeX": sx, "sizeY": sy, "autoHeight": False},
        "parameterMappings": {
            n: {"name": n, "type": "dashboard-level", "mapTo": n, "value": None, "title": ""} for n in param_names
        },
    }
