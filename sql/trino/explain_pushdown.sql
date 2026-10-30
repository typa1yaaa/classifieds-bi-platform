EXPLAIN
SELECT category_id, COUNT(*) AS contacts
FROM clickhouse.raw.events
WHERE event_type = 'contact' AND event_date >= DATE '2026-09-01'
GROUP BY category_id;

EXPLAIN
SELECT category_id, SUM(contacts) AS contacts
FROM clickhouse.marts.fct_category_daily
WHERE event_date >= DATE '2026-09-01'
GROUP BY category_id;

EXPLAIN
SELECT c.name, o.service_type, SUM(f.contacts) AS contacts
FROM vertica.finance.promo_orders AS o
JOIN clickhouse.marts.fct_listing_daily AS f ON f.listing_id = o.listing_id
JOIN postgresql.public.listings AS l ON l.listing_id = o.listing_id
JOIN postgresql.public.categories AS c ON c.category_id = l.category_id
WHERE o.status = 'paid' AND f.event_date >= DATE '2026-09-01'
GROUP BY c.name, o.service_type;
