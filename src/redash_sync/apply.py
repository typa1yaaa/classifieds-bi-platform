from __future__ import annotations

import sys

from src.redash_sync.client import Redash, RedashError
from src.redash_sync.spec import (build_parameter, default_parameter_values, load_dashboards, load_data_sources,
                                  load_snippets, query_sql, validate, viz_options, viz_type, widget_options)


def apply_data_sources(rd: Redash) -> dict[str, int]:
    existing = {d["name"]: d for d in rd.data_sources()}
    ids = {}
    for ds in load_data_sources():
        payload = {"name": ds["name"], "type": ds["type"], "options": ds["options"]}
        if ds["name"] in existing:
            ds_id = existing[ds["name"]]["id"]
            rd.post(f"data_sources/{ds_id}", payload)
        else:
            ds_id = rd.post("data_sources", payload)["id"]
        ids[ds["key"]] = ds_id
        print(f"data source  {ds['name']} (id={ds_id})")
    return ids


def apply_snippets(rd: Redash) -> None:
    existing = {s["trigger"]: s for s in rd.get("query_snippets")}
    for sn in load_snippets():
        if sn["trigger"] in existing:
            rd.post(f"query_snippets/{existing[sn['trigger']]['id']}", sn)
        else:
            rd.post("query_snippets", sn)
    print(f"snippets     {len(load_snippets())}")


def schedule(seconds: int | None) -> dict | None:
    return None if not seconds else {"interval": seconds, "until": None, "day_of_week": None, "time": None}


def apply_dashboard(rd: Redash, spec, ds_ids: dict[str, int], existing_queries: dict[str, dict]) -> None:
    # --- запросы. Сначала те, на которые ссылаются параметры-выпадающие списки.
    order = sorted(spec.queries, key=lambda q: 0 if not q.get("params") else 1)
    query_ids: dict[str, int] = {}
    viz_ids: dict[str, int] = {}
    for q in order:
        params = [build_parameter(n, spec.parameters[n], query_ids) for n in q.get("params", [])]
        payload = {
            "name": q["name"],
            "query": query_sql(q),
            "data_source_id": ds_ids[q["data_source"]],
            "description": "",
            "schedule": schedule(q.get("schedule")),
            "options": {"parameters": params},
        }
        if q["name"] in existing_queries:
            qid = existing_queries[q["name"]]["id"]
            rd.post(f"queries/{qid}", payload)
        else:
            qid = rd.post("queries", payload)["id"]
        rd.post(f"queries/{qid}", {"is_draft": False, "tags": q.get("tags", [])})
        query_ids[q["key"]] = qid

        current = {v["name"]: v for v in rd.query(qid).get("visualizations", [])}
        for v in q.get("visualizations", []):
            payload = {"name": v["name"], "type": viz_type(v), "options": viz_options(v), "description": ""}
            if v["name"] in current:
                vid = current[v["name"]]["id"]
                rd.post(f"visualizations/{vid}", payload)
            else:
                vid = rd.post("visualizations", {**payload, "query_id": qid})["id"]
            viz_ids[f"{q['key']}.{v['key']}"] = vid

    dashboards = {d["name"]: d for d in rd.dashboards()}
    if spec.name in dashboards:
        dash = rd.dashboard(dashboards[spec.name])
        for w in dash.get("widgets", []) or []:
            rd.delete(f"widgets/{w['id']}")
    else:
        dash = rd.post("dashboards", {"name": spec.name})

    qkey_params = {q["key"]: q.get("params", []) for q in spec.queries}
    for w in spec.widgets:
        if "text" in w:
            payload = {"dashboard_id": dash["id"], "visualization_id": None, "text": w["text"], "width": 1,
                       "options": widget_options(w, [])}
        else:
            qk = w["viz"].split(".")[0]
            payload = {"dashboard_id": dash["id"], "visualization_id": viz_ids[w["viz"]], "text": "", "width": 1,
                       "options": widget_options(w, qkey_params[qk])}
        rd.post("widgets", payload)
    rd.post(f"dashboards/{dash['id']}", {"name": spec.name, "tags": spec.tags, "is_draft": False,
                                         "dashboard_filters_enabled": bool(spec.parameters)})
    print(f"dashboard    {spec.name}: {len(spec.queries)} запросов, {len(spec.widgets)} виджетов")

    existing_alerts = {a["name"]: a for a in rd.get("alerts")}
    for q in spec.queries:
        if "alert" not in q:
            continue
        a = q["alert"]
        payload = {"name": a["name"], "query_id": query_ids[q["key"]], "rearm": 0,
                   "options": {"column": a["column"], "op": a["op"], "value": a["value"], "muted": False}}
        if a["name"] in existing_alerts:
            rd.post(f"alerts/{existing_alerts[a['name']]['id']}", payload)
        else:
            rd.post("alerts", payload)
        print(f"alert        {a['name']}")

    for q in spec.queries:
        try:
            rd.refresh(query_ids[q["key"]], default_parameter_values(q.get("params", []), spec.parameters))
        except RedashError as e:
            print(f"  ! {q['name']}: {e}")


def main() -> None:
    specs = load_dashboards()
    errors = validate(specs)
    if errors:
        print("Ошибки в спецификациях:\n  " + "\n  ".join(errors))
        sys.exit(1)
    rd = Redash()
    ds_ids = apply_data_sources(rd)
    apply_snippets(rd)
    existing_queries = {q["name"]: q for q in rd.queries()}
    for spec in specs:
        apply_dashboard(rd, spec, ds_ids, existing_queries)


if __name__ == "__main__":
    main()
