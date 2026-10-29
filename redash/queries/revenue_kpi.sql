WITH bounds AS (
    SELECT DATE '{{ period.start }}' AS d1,
           DATE '{{ period.end }}'   AS d2,
           DATE '{{ period.start }}' - (DATE '{{ period.end }}' - DATE '{{ period.start }}' + 1) AS p1,
           DATE '{{ period.start }}' - 1 AS p2
),
cur AS (
    SELECT SUM(amount) AS revenue, COUNT(*) AS orders, COUNT(DISTINCT seller_id) AS sellers
    FROM finance.promo_orders, bounds
    WHERE status = 'paid' AND CAST(created_at AS DATE) BETWEEN d1 AND d2
),
prev AS (
    SELECT SUM(amount) AS revenue, COUNT(*) AS orders, COUNT(DISTINCT seller_id) AS sellers
    FROM finance.promo_orders, bounds
    WHERE status = 'paid' AND CAST(created_at AS DATE) BETWEEN p1 AND p2
)
SELECT cur.revenue AS revenue,
       prev.revenue AS revenue_prev,
       cur.orders AS orders,
       prev.orders AS orders_prev,
       cur.sellers AS paying_sellers,
       prev.sellers AS paying_sellers_prev,
       cur.revenue / NULLIF(cur.sellers, 0) AS arppu,
       prev.revenue / NULLIF(prev.sellers, 0) AS arppu_prev
FROM cur, prev
