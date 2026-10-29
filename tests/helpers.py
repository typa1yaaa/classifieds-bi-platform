from __future__ import annotations

from src.redash_sync.spec import render_default_params as render_params  # noqa: F401


def viz_columns(q: dict) -> set[str]:
    cols = set()
    for v in q.get("visualizations", []):
        if v["type"] == "counter":
            cols |= {v["value"], *([v["target"]] if v.get("target") else [])}
        elif v["type"] == "chart":
            cols |= {v["x"], *v.get("y", [])}
            cols |= {c for c in [v.get("series"), v.get("z")] if c}
    return cols
