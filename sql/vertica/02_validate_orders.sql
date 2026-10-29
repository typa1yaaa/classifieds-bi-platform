INSERT INTO finance.promo_orders_quarantine
    (order_id, listing_id, seller_id, service_type, created_at, amount, status, reason)
SELECT order_id, listing_id, seller_id, service_type, created_at, amount, status,
       CASE
           WHEN seller_id IS NULL THEN 'missing_seller_id'
           WHEN listing_id IS NULL THEN 'missing_listing_id'
           WHEN created_at IS NULL THEN 'missing_created_at'
           WHEN amount IS NULL OR amount <= 0 THEN 'non_positive_amount'
           WHEN status NOT IN ('paid', 'cancelled', 'refunded') THEN 'unknown_status'
           WHEN service_type NOT IN ('bump', 'highlight', 'premium') THEN 'unknown_service'
       END AS reason
FROM finance.promo_orders_stg
WHERE seller_id IS NULL OR listing_id IS NULL OR created_at IS NULL
   OR amount IS NULL OR amount <= 0
   OR status NOT IN ('paid', 'cancelled', 'refunded')
   OR service_type NOT IN ('bump', 'highlight', 'premium');

INSERT INTO finance.promo_orders
SELECT order_id, listing_id, seller_id, service_type, created_at, amount, status, active_from, active_to
FROM finance.promo_orders_stg
WHERE seller_id IS NOT NULL AND listing_id IS NOT NULL AND created_at IS NOT NULL
  AND amount > 0
  AND status IN ('paid', 'cancelled', 'refunded')
  AND service_type IN ('bump', 'highlight', 'premium');
