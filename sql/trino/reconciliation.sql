SELECT 'orders_without_listing' AS check_name,
       'DWH и PostgreSQL' AS systems,
       COUNT(*) AS violations
FROM vertica.finance.promo_orders AS o
LEFT JOIN postgresql.public.listings AS l ON l.listing_id = o.listing_id
WHERE l.listing_id IS NULL

UNION ALL

SELECT 'order_seller_mismatch', 'DWH и PostgreSQL', COUNT(*)
FROM vertica.finance.promo_orders AS o
JOIN postgresql.public.listings AS l ON l.listing_id = o.listing_id
WHERE l.seller_id <> o.seller_id

UNION ALL

SELECT 'paid_promo_day_not_flagged', 'DWH и ClickHouse', COUNT(*)
FROM vertica.finance.promo_orders AS o
JOIN clickhouse.marts.fct_listing_daily AS f
  ON  f.listing_id = o.listing_id
  AND f.event_date BETWEEN CAST(o.active_from AS date)
                       AND date_add('day', -1, CAST(o.active_to AS date))
WHERE o.status = 'paid'
  AND f.event_date >= DATE '2026-03-01'
  AND f.is_promoted = 0

UNION ALL

SELECT 'promo_effect_revenue_diff', 'DWH и ClickHouse',
       CAST(ABS(
           (SELECT SUM(amount) FROM vertica.finance.promo_orders WHERE status = 'paid')
         - (SELECT SUM(amount) FROM clickhouse.marts.promo_order_effect)
       ) AS bigint)
