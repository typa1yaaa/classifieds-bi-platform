INSERT INTO raw.events
    (event_id, event_time, event_type, user_id, listing_id, seller_id, category_id, region_id,
     platform, is_promoted, promo_service, ingested_at)
SELECT
    event_id,
    event_time,
    event_type,
    user_id,
    listing_id,
    seller_id,
    category_id,
    region_id,
    platform,
    is_promoted,
    promo_service,
    event_time + toIntervalSecond(5 + (cityHash64(event_id, 7) % 120) + dup * 3600) AS ingested_at
FROM
(
    SELECT
        cityHash64(listing_id, day, imp_k, stage.2) AS event_id,
        t_imp + toIntervalSecond(stage.3) AS event_time,
        stage.2 AS event_type,
        user_id, listing_id, seller_id, category_id, region_id, platform,
        is_promoted, promo_service
    FROM
    (
        SELECT
            *,
            imp_k,
            cityHash64(listing_id, day, imp_k) AS h,
            toUInt32(cityHash64(h, 10) % {n_users} + 1) AS user_id,
            multiIf(cityHash64(user_id, 777) % 100 < 42, 'android',
                    cityHash64(user_id, 777) % 100 < 80, 'ios', 'web') AS platform,
            least(0.95, base_ctr * ctr_mult
                        * multiIf(platform = 'ios', 1.05, platform = 'web', 0.85, 1.0)) AS ctr,
            base_cr
                * if(is_promoted = 1, 0.92, 1.0)
                * multiIf(platform = 'web', 1.10, 1.0)
                * if(platform = 'ios' AND day >= toDate('{ios_release_date}'), 0.62, 1.0) AS cr,
            ((cityHash64(h, 1) % 1000000) / 1e6) < ctr AS is_view,
            is_view AND ((cityHash64(h, 2) % 1000000) / 1e6) < cr AS is_contact,
            is_view AND ((cityHash64(h, 3) % 1000000) / 1e6) < 0.07 AS is_fav,
            toDateTime(day, 'UTC') + toIntervalSecond(28800 + cityHash64(h, 11) % 54000) AS t_imp,
            toUInt32(10 + cityHash64(h, 12) % 290) AS dv,
            toUInt32(30 + cityHash64(h, 13) % 870) AS dc,
            toUInt32(20 + cityHash64(h, 14) % 580) AS df,
            arrayFilter(s -> s.1 = 1, [
                (toUInt8(1), 'impression', toUInt32(0)),
                (toUInt8(is_view), 'view', dv),
                (toUInt8(is_contact), 'contact', dv + dc),
                (toUInt8(is_fav), 'favorite', dv + df)
            ]) AS stages
        FROM
        (
            SELECT
                ld.listing_id AS listing_id, ld.seller_id AS seller_id, ld.category_id AS category_id,
                ld.region_id AS region_id, ld.day AS day, ld.base_ctr AS base_ctr, ld.base_cr AS base_cr,
                p.imp_mult > 0 AS is_promoted_b,
                toUInt8(is_promoted_b) AS is_promoted,
                p.service_type AS promo_service,
                if(is_promoted_b, p.ctr_mult, 1.0) AS ctr_mult,
                {scale} * 1.6 * ld.popularity * ld.imp_factor
                    * [1.0, 0.97, 0.96, 0.95, 0.92, 1.10, 1.15][toDayOfWeek(ld.day)]
                    * (0.4 + 0.9 * exp(-dateDiff('day', ld.created_date, ld.day) / 20.0))
                    * (1 + 0.15 * dateDiff('day', toDate('{start_date}'), ld.day) / {days})
                    * if(is_promoted_b, p.imp_mult, 1.0) AS lambda,
                -- лог-нормальный шум через Box-Muller на хешах
                sqrt(-2 * log((cityHash64(ld.listing_id, ld.day, 1) % 1000000 + 0.5) / 1e6))
                    * cos(2 * pi() * ((cityHash64(ld.listing_id, ld.day, 2) % 1000000) / 1e6)) AS z,
                lambda * exp(0.35 * z - 0.06125) AS x,
                toUInt32(floor(x) + (((cityHash64(ld.listing_id, ld.day, 3) % 1000000) / 1e6) < x - floor(x))) AS n_imp
            FROM
            (
                SELECT l.*, addDays(greatest(l.created_date, toDate('{d_from}')), off) AS day
                FROM gen.listings AS l
                ARRAY JOIN range(toUInt32(greatest(0,
                    dateDiff('day', greatest(l.created_date, toDate('{d_from}')),
                                    least(l.closed_date - 1, toDate('{d_to}'))) + 1))) AS off
                WHERE l.created_date <= toDate('{d_to}') AND l.closed_date > toDate('{d_from}')
            ) AS ld
            LEFT JOIN
            (
                SELECT listing_id, day, service_type, imp_mult, ctr_mult
                FROM gen.promo_days
                WHERE day BETWEEN toDate('{d_from}') AND toDate('{d_to}')
            ) AS p ON p.listing_id = ld.listing_id AND p.day = ld.day
        )
        ARRAY JOIN range(n_imp) AS imp_k
    )
    ARRAY JOIN stages AS stage
)
ARRAY JOIN if(cityHash64(event_id, 99) % 1000 < 3, [0, 1], [0]) AS dup
WHERE NOT (toDate(event_time) = toDate('{incident_date}') AND platform = 'android'
           AND toHour(event_time) BETWEEN 10 AND 17)
SETTINGS join_use_nulls = 0, max_threads = 4;
