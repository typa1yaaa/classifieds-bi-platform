from __future__ import annotations


import numpy as np
import pandas as pd

from src.common.config import GenConfig

CATEGORY_TREE = [
    (1, "Транспорт", [
        ("Автомобили", 1.6, 0.11, 0.050, 1_250_000),
        ("Мотоциклы", 0.7, 0.10, 0.045, 320_000),
        ("Запчасти", 1.0, 0.09, 0.070, 6_500),
    ]),
    (2, "Недвижимость", [
        ("Квартиры", 1.5, 0.12, 0.055, 7_800_000),
        ("Аренда квартир", 1.8, 0.14, 0.085, 45_000),
        ("Дома и дачи", 0.8, 0.10, 0.040, 4_200_000),
    ]),
    (3, "Электроника", [
        ("Телефоны", 1.4, 0.13, 0.080, 24_000),
        ("Ноутбуки", 1.0, 0.12, 0.070, 48_000),
        ("Аудио и видео", 0.8, 0.10, 0.065, 9_000),
    ]),
    (4, "Дом и сад", [
        ("Мебель", 1.0, 0.09, 0.060, 12_000),
        ("Бытовая техника", 1.1, 0.10, 0.075, 15_000),
        ("Ремонт и строительство", 0.9, 0.08, 0.065, 3_500),
    ]),
    (5, "Одежда", [
        ("Женская одежда", 1.2, 0.08, 0.045, 2_200),
        ("Мужская одежда", 0.9, 0.08, 0.045, 2_600),
        ("Детская одежда", 1.0, 0.09, 0.055, 1_200),
    ]),
    (6, "Услуги", [
        ("Ремонт квартир", 0.9, 0.10, 0.090, 25_000),
        ("Красота и здоровье", 0.8, 0.09, 0.085, 2_000),
        ("Обучение", 0.6, 0.09, 0.080, 1_800),
    ]),
]

REGIONS = [
    ("Москва", "Центральный", 13.0), ("Московская область", "Центральный", 8.5),
    ("Санкт-Петербург", "Северо-Западный", 5.6), ("Ленинградская область", "Северо-Западный", 2.0),
    ("Краснодарский край", "Южный", 5.8), ("Ростовская область", "Южный", 4.1),
    ("Свердловская область", "Уральский", 4.2), ("Челябинская область", "Уральский", 3.4),
    ("Тюменская область", "Уральский", 1.6), ("Новосибирская область", "Сибирский", 2.8),
    ("Красноярский край", "Сибирский", 2.8), ("Омская область", "Сибирский", 1.8),
    ("Республика Татарстан", "Приволжский", 4.0), ("Нижегородская область", "Приволжский", 3.1),
    ("Самарская область", "Приволжский", 3.1), ("Республика Башкортостан", "Приволжский", 4.0),
    ("Пермский край", "Приволжский", 2.5), ("Воронежская область", "Центральный", 2.3),
    ("Волгоградская область", "Южный", 2.4), ("Приморский край", "Дальневосточный", 1.8),
    ("Хабаровский край", "Дальневосточный", 1.3), ("Иркутская область", "Сибирский", 2.3),
    ("Калининградская область", "Северо-Западный", 1.0), ("Ставропольский край", "Северо-Кавказский", 2.8),
]

PLATFORMS = ["android", "ios", "web"]
PLATFORM_WEIGHTS = [0.42, 0.38, 0.20]


def build_categories() -> pd.DataFrame:
    rows = []
    leaf_id = 100
    for parent_id, parent_name, leaves in CATEGORY_TREE:
        rows.append(dict(category_id=parent_id, parent_id=None, name=parent_name, is_leaf=False,
                         imp_factor=None, base_ctr=None, base_cr=None, price_median=None))
        for name, imp, ctr, cr, price in leaves:
            leaf_id += 1
            rows.append(dict(category_id=leaf_id, parent_id=parent_id, name=name, is_leaf=True,
                             imp_factor=imp, base_ctr=ctr, base_cr=cr, price_median=price))
    df = pd.DataFrame(rows)
    df["parent_id"] = df["parent_id"].astype("Int64")
    return df


def build_regions() -> pd.DataFrame:
    return pd.DataFrame(
        [dict(region_id=i + 1, name=n, federal_district=fd, population_weight=w)
         for i, (n, fd, w) in enumerate(REGIONS)]
    )


def build_all(cfg: GenConfig) -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(cfg.seed)
    start = pd.Timestamp(cfg.start_date)
    end = pd.Timestamp(cfg.end_date)

    categories = build_categories()
    regions = build_regions()
    leaves = categories[categories.is_leaf].reset_index(drop=True)
    reg_w = regions.population_weight.to_numpy() / regions.population_weight.sum()

    n_s = cfg.n_sellers
    seller_type = np.where(rng.random(n_s) < 0.15, "company", "private")
    sellers = pd.DataFrame({
        "seller_id": np.arange(1, n_s + 1),
        "seller_type": seller_type,
        "region_id": rng.choice(regions.region_id, size=n_s, p=reg_w),
        "registered_at": start - pd.to_timedelta(rng.integers(0, 3 * 365, n_s), unit="D"),
    })
    seller_propensity = rng.lognormal(0.0, 1.0, n_s) * np.where(seller_type == "company", 2.5, 1.0)
    seller_active_days = rng.exponential(110, n_s).astype(int) + 14
    seller_first_day = rng.integers(-60, cfg.days, n_s)

    n_l = cfg.n_listings

    s_weights = np.where(seller_type == "company", 6.0, 1.0)
    s_idx = rng.choice(n_s, size=n_l, p=s_weights / s_weights.sum())
    cat_w = leaves.imp_factor.to_numpy()
    c_idx = rng.choice(len(leaves), size=n_l, p=cat_w / cat_w.sum())

    region = np.where(rng.random(n_l) < 0.9, sellers.region_id.to_numpy()[s_idx],
                      rng.choice(regions.region_id, size=n_l, p=reg_w))
    created_off = rng.integers(-150, cfg.days, n_l)
    lifetime = (rng.exponential(45, n_l) + 7).astype(int)
    created_at = start + pd.to_timedelta(created_off, unit="D") + pd.to_timedelta(
        rng.integers(0, 86400, n_l), unit="s")
    closed_at = created_at + pd.to_timedelta(lifetime, unit="D")
    status = np.where(closed_at > end + pd.Timedelta(days=1), "active",
                      np.where(rng.random(n_l) < 0.6, "sold", "archived"))
    price = (leaves.price_median.to_numpy()[c_idx] * rng.lognormal(0, 0.5, n_l)).round(-1)

    listings = pd.DataFrame({
        "listing_id": np.arange(1, n_l + 1),
        "seller_id": sellers.seller_id.to_numpy()[s_idx],
        "category_id": leaves.category_id.to_numpy()[c_idx],
        "region_id": region,
        "price": price,
        "created_at": created_at,
        "closed_at": pd.Series(closed_at).where(status != "active"),
        "status": status,
    })


    popularity = rng.lognormal(0.0, 0.8, n_l)
    latent = pd.DataFrame({
        "listing_id": listings.listing_id,
        "seller_id": listings.seller_id,
        "category_id": listings.category_id,
        "parent_category_id": leaves.parent_id.to_numpy()[c_idx].astype(int),
        "region_id": listings.region_id,
        "created_date": listings.created_at.dt.date,
        "closed_date": closed_at.date,
        "popularity": popularity.round(4),
        "imp_factor": cat_w[c_idx],
        "base_ctr": leaves.base_ctr.to_numpy()[c_idx] * np.clip(popularity, 0.3, 3) ** 0.25,
        "base_cr": 2.0 * leaves.base_cr.to_numpy()[c_idx] * rng.lognormal(0, 0.25, n_l),
    })

    n_u = cfg.n_users
    users = pd.DataFrame({
        "user_id": np.arange(1, n_u + 1),
        "region_id": rng.choice(regions.region_id, size=n_u, p=reg_w),
        "registered_at": start - pd.to_timedelta(rng.integers(0, 5 * 365, n_u), unit="D"),
    })

    seller_latent = pd.DataFrame({
        "seller_id": sellers.seller_id,
        "propensity": seller_propensity,
        "first_promo_day": seller_first_day,
        "active_days": seller_active_days,
    })

    categories_out = categories[["category_id", "parent_id", "name", "is_leaf"]].assign(
        is_leaf=lambda d: d.is_leaf.map({True: "true", False: "false"}))
    return dict(categories=categories_out, categories_full=categories, regions=regions,
                sellers=sellers, listings=listings, users=users,
                listing_latent=latent, seller_latent=seller_latent)


