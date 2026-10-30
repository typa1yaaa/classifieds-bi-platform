WITH orders AS (
    SELECT
        o.order_id,
        o.listing_id,
        o.seller_id,
        o.service_type,
        o.amount,
        CAST(o.active_from AS date) AS d_from,
        date_diff('day', CAST(o.active_from AS date), CAST(o.active_to AS date)) AS promo_days
    FROM vertica.finance.promo_orders AS o
    WHERE o.status = 'paid'
),
activity AS (
    SELECT listing_id, event_date, impressions, views, contacts, is_promoted
    FROM clickhouse.marts.fct_listing_daily
    WHERE event_date >= DATE '2026-03-01'
),
per_order AS (
    SELECT
        o.order_id AS order_id,
        SUM(CASE WHEN a.event_date >= o.d_from THEN a.contacts ELSE 0 END) AS contacts_promo,
        SUM(CASE WHEN a.event_date <  o.d_from THEN a.contacts ELSE 0 END) AS contacts_before,
        SUM(CASE WHEN a.event_date >= o.d_from THEN a.impressions ELSE 0 END) AS impressions_promo,
        SUM(CASE WHEN a.event_date <  o.d_from THEN a.impressions ELSE 0 END) AS impressions_before,
        SUM(CASE WHEN a.event_date <  o.d_from THEN a.is_promoted ELSE 0 END) AS promoted_days_before
    FROM orders AS o
    JOIN activity AS a
      ON  a.listing_id = o.listing_id
      AND a.event_date BETWEEN date_add('day', -14, o.d_from) AND date_add('day', o.promo_days - 1, o.d_from)
    GROUP BY o.order_id
)
SELECT
    o.order_id AS order_id,
    o.listing_id AS listing_id,
    o.seller_id AS seller_id,
    l.category_id AS category_id,
    c.parent_id AS parent_category_id,
    l.region_id AS region_id,
    o.service_type AS service_type,
    o.amount AS amount,
    o.d_from AS promo_start_date,
    o.promo_days AS promo_days,
    COALESCE(p.contacts_promo, 0) AS contacts_promo,
    COALESCE(p.contacts_before, 0) AS contacts_before,
    COALESCE(p.impressions_promo, 0) AS impressions_promo,
    COALESCE(p.impressions_before, 0)  AS impressions_before,
    CAST(COALESCE(p.contacts_promo, 0) AS double) / o.promo_days AS contacts_per_day_promo,
    CAST(COALESCE(p.contacts_before, 0) AS double) / 14 AS contacts_per_day_before,
    (CAST(COALESCE(p.contacts_promo, 0) AS double) / o.promo_days
       - CAST(COALESCE(p.contacts_before, 0) AS double) / 14) * o.promo_days AS extra_contacts,
    CASE
        WHEN date_diff('day', CAST(l.created_at AS date), o.d_from) >= 14
         AND COALESCE(p.promoted_days_before, 0) = 0
        THEN 1 ELSE 0
    END AS is_eligible
FROM orders AS o
LEFT JOIN per_order AS p ON p.order_id = o.order_id
JOIN postgresql.public.listings AS l ON l.listing_id = o.listing_id
JOIN postgresql.public.categories AS c ON c.category_id = l.category_id
