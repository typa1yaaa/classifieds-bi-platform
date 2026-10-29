from __future__ import annotations

import json
import re

from src.redash_sync.client import Redash
from src.redash_sync.spec import REDASH_DIR

KEEP_QUERY = ["id", "name", "description", "query", "data_source_id", "schedule", "tags", "options", "is_draft"]
KEEP_VIZ = ["id", "name", "type", "options"]


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "item"


def main() -> None:
    rd = Redash()
    out = REDASH_DIR / "_export"
    (out / "queries").mkdir(parents=True, exist_ok=True)
    (out / "dashboards").mkdir(parents=True, exist_ok=True)

    for q in rd.queries():
        full = rd.query(q["id"])
        doc = {k: full.get(k) for k in KEEP_QUERY}
        doc["visualizations"] = [{k: v.get(k) for k in KEEP_VIZ} for v in full.get("visualizations", [])]
        (out / "queries" / f"{q['id']:04d}-{slug(q['name'])}.json").write_text(
            json.dumps(doc, ensure_ascii=False, indent=2, sort_keys=True))

    for d in rd.dashboards():
        full = rd.dashboard(d)
        doc = {"id": full["id"], "name": full["name"], "tags": full.get("tags"),
               "widgets": [{"visualization_id": (w.get("visualization") or {}).get("id"),
                            "text": w.get("text"), "position": w["options"].get("position")}
                           for w in full.get("widgets", [])]}
        (out / "dashboards" / f"{full['id']:04d}-{slug(full['name'])}.json").write_text(
            json.dumps(doc, ensure_ascii=False, indent=2, sort_keys=True))
    print(f"exported to {out}")


if __name__ == "__main__":
    main()
