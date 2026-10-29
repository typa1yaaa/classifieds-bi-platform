from __future__ import annotations

import numpy as np
import pandas as pd

from src.common.config import GenConfig

SERVICES = {
    #share, days, price_mult, imp_mult, ctr_mult
    "bump":      (0.55, 3, 1.0, 2.2, 1.00),
    "highlight": (0.30, 7, 1.6, 1.4, 1.35),
    "premium":   (0.15, 7, 4.0, 4.0, 1.10),
}

BASE_PRICE = {1: 249, 2: 399, 3: 149, 4: 99, 5: 59, 6: 179}
WEEKDAY_ORDERS = [1.05, 1.0, 1.0, 0.98, 0.95, 1.08, 1.02]


def build_orders(cfg: GenConfig, latent: pd.DataFrame, seller_latent: pd.DataFrame,
                 orders_per_day: float = 220.0) -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(cfg.seed + 1)
    start = pd.Timestamp(cfg.start_date)

    created = (pd.to_datetime(latent.created_date) - start).dt.days.to_numpy()
    closed = (pd.to_datetime(latent.closed_date) - start).dt.days.to_numpy()
    pop = latent.popularity.to_numpy()
    seller_ids = latent.seller_id.to_numpy()

    sl = seller_latent.set_index("seller_id")
    s_prop = sl.propensity.reindex(seller_ids).to_numpy()
    s_first = sl.first_promo_day.reindex(seller_ids).to_numpy()
    s_last = s_first + sl.active_days.reindex(seller_ids).to_numpy()
    base_w = pop ** 1.3 * s_prop

    services = list(SERVICES)
    shares = np.array([SERVICES[s][0] for s in services])

    rows = []
    for d in range(cfg.days):
        dt = start + pd.Timedelta(days=d)
        trend = 1.0 + 0.25 * d / cfg.days
        n = rng.poisson(orders_per_day * cfg.n_listings / 150_000 * trend * WEEKDAY_ORDERS[dt.day_of_week])
        mask = (created <= d) & (closed > d) & (s_first <= d) & (s_last > d)
        idx = np.flatnonzero(mask)
        if len(idx) == 0 or n == 0:
            continue
        w = base_w[idx]
        pick = rng.choice(idx, size=n, p=w / w.sum())
        svc = rng.choice(services, size=n, p=shares)
        secs = rng.integers(7 * 3600, 23 * 3600, n)
        for li, sv, sc in zip(pick, svc, secs):
            rows.append((int(latent.listing_id.iat[li]), int(seller_ids[li]),
                         int(latent.parent_category_id.iat[li]), sv, dt + pd.Timedelta(seconds=int(sc))))

    orders = pd.DataFrame(rows, columns=["listing_id", "seller_id", "parent_category_id", "service_type", "created_at"])
    orders.insert(0, "order_id", np.arange(1, len(orders) + 1))
    n = len(orders)

    price_mult = orders.service_type.map({k: v[2] for k, v in SERVICES.items()}).to_numpy()
    base = orders.parent_category_id.map(BASE_PRICE).to_numpy()
    discount = np.where(rng.random(n) < 0.10, 0.8, 1.0)
    orders["amount"] = (base * price_mult * discount).round(2)

    r = rng.random(n)
    orders["status"] = np.where(r < 0.92, "paid", np.where(r < 0.97, "cancelled", "refunded"))
    duration = orders.service_type.map({k: v[1] for k, v in SERVICES.items()}).to_numpy()
    delay = pd.to_timedelta(rng.integers(30, 1800, n), unit="s")
    orders["active_from"] = orders.created_at + delay
    orders["active_to"] = orders.active_from + pd.to_timedelta(duration, unit="D")
    refunded = orders.status == "refunded"
    orders.loc[refunded, "active_to"] = orders.loc[refunded, "active_from"] + pd.Timedelta(days=1)
    cancelled = orders.status == "cancelled"
    orders.loc[cancelled, ["active_from", "active_to"]] = pd.NaT
    orders = orders.drop(columns=["parent_category_id"])

    promo_days = _promo_days(orders)
    return orders, promo_days


def _promo_days(orders: pd.DataFrame) -> pd.DataFrame:
    act = orders[orders.status.isin(["paid", "refunded"])]
    recs = []
    for o in act.itertuples(index=False):
        d0 = o.active_from.normalize()
        d1 = (o.active_to - pd.Timedelta(seconds=1)).normalize()
        _, _, _, imp, ctr = SERVICES[o.service_type]
        for day in pd.date_range(d0, d1, freq="D"):
            recs.append((o.listing_id, day.date(), o.service_type, imp, ctr))
    pdays = pd.DataFrame(recs, columns=["listing_id", "day", "service_type", "imp_mult", "ctr_mult"])

    pdays = (pdays.sort_values("imp_mult", ascending=False)
             .groupby(["listing_id", "day"], as_index=False)
             .agg(service_type=("service_type", "first"), imp_mult=("imp_mult", "max"), ctr_mult=("ctr_mult", "max")))
    return pdays


def add_dirty_rows(orders: pd.DataFrame, cfg: GenConfig, share: float = 0.004) -> pd.DataFrame:
    rng = np.random.default_rng(cfg.seed + 2)
    out = orders.copy()
    for col in ["created_at", "active_from", "active_to"]:
        out[col] = out[col].dt.strftime("%Y-%m-%d %H:%M:%S")
    out["seller_id"] = out["seller_id"].astype(str)
    out["amount"] = out["amount"].map(lambda v: f"{v:.2f}")
    k = max(3, int(len(out) * share))
    bad = out.sample(k, random_state=cfg.seed).copy()
    bad["order_id"] = np.arange(out.order_id.max() + 1, out.order_id.max() + 1 + k)
    kind = rng.permutation(np.arange(k) % 3)
    bad.loc[kind == 0, "amount"] = bad.loc[kind == 0, "amount"].map(lambda v: f"-{v}")
    bad.loc[kind == 1, "seller_id"] = ""
    bad.loc[kind == 2, "created_at"] = "2026-13-45 25:61:00"
    return pd.concat([out, bad], ignore_index=True).sort_values("order_id")
