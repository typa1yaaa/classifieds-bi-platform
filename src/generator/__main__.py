from __future__ import annotations

import time

from src.common.config import GEN
from src.generator.orders import add_dirty_rows, build_orders
from src.generator.reference import build_all


def main() -> None:
    t0 = time.time()
    out = GEN.data_dir
    gen = GEN.gen_dir
    out.mkdir(parents=True, exist_ok=True)
    gen.mkdir(parents=True, exist_ok=True)

    ref = build_all(GEN)
    for name in ["categories", "regions", "sellers", "listings", "users"]:
        ref[name].to_csv(out / f"{name}.csv", index=False)
    ref["listing_latent"].to_csv(gen / "listing_latent.csv", index=False)
    ref["categories_full"].to_csv(gen / "categories_full.csv", index=False)

    orders, promo_days = build_orders(GEN, ref["listing_latent"], ref["seller_latent"])
    add_dirty_rows(orders, GEN).to_csv(out / "promo_orders.csv", index=False)
    promo_days.to_csv(gen / "promo_days.csv", index=False)

    print(f"listings={len(ref['listings']):,} sellers={len(ref['sellers']):,} users={len(ref['users']):,} "
          f"orders={len(orders):,} promo_days={len(promo_days):,} in {time.time() - t0:.1f}s -> {out}")


if __name__ == "__main__":
    main()
