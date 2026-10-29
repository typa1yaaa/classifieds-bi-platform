CREATE PROJECTION IF NOT EXISTS finance.promo_orders_by_seller AS
SELECT seller_id, created_at, order_id, listing_id, service_type, amount, status
FROM finance.promo_orders
ORDER BY seller_id, created_at
SEGMENTED BY HASH(seller_id) ALL NODES;

CREATE PROJECTION IF NOT EXISTS finance.promo_orders_by_listing AS
SELECT listing_id, created_at, order_id, seller_id, service_type, amount, status, active_from, active_to
FROM finance.promo_orders
ORDER BY listing_id, created_at
SEGMENTED BY HASH(listing_id) ALL NODES;

SELECT START_REFRESH();

SELECT ANALYZE_STATISTICS('finance.promo_orders');
SELECT ANALYZE_STATISTICS('finance.dim_listing');
