from __future__ import annotations

import os
import random

from src.redash_sync.client import Redash
from src.redash_sync.spec import load_dashboards

WEIGHTS = {"finance": 5, "self-service": 8, "product": 4, "dq": 3, "governance": 1}


def main(total_views: int = 300, seed: int = 7) -> None:
    rnd = random.Random(seed)
    keys = [k for k in os.environ.get("REDASH_SIM_USER_KEYS", "").split(",") if k] or [None]
    clients = [Redash(api_key=k) for k in keys]
    by_name = {d["name"]: d for d in clients[0].dashboards()}

    targets, weights = [], []
    for spec in load_dashboards():
        if not spec.simulate_views or spec.name not in by_name:
            continue
        targets.append(by_name[spec.name])
        weights.append(max((WEIGHTS.get(t, 1) for t in spec.tags), default=1))

    for _ in range(total_views):
        dash = rnd.choices(targets, weights)[0]
        rnd.choice(clients).dashboard(dash)
    print(f"{total_views} просмотров {len(targets)} дашбордов от {len(clients)} пользователей")


if __name__ == "__main__":
    main()
