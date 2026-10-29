DROP TABLE IF EXISTS finance.fct_promo_revenue_daily;

CREATE TABLE finance.fct_promo_revenue_daily AS
SELECT
    CAST(o.created_at AS DATE) AS order_date,
    l.category_id,
    c.parent_id AS parent_category_id,
    l.region_id,
    o.service_type,
    s.seller_type,
    SUM(CASE WHEN o.status = 'paid' THEN 1 ELSE 0 END) AS orders_paid,
    SUM(CASE WHEN o.status = 'refunded' THEN 1 ELSE 0 END) AS orders_refunded,
    SUM(CASE WHEN o.status = 'cancelled' THEN 1 ELSE 0 END) AS orders_cancelled,
    SUM(CASE WHEN o.status = 'paid' THEN o.amount ELSE 0 END) AS revenue,
    SUM(CASE WHEN o.status = 'refunded' THEN o.amount ELSE 0 END) AS refunds,
    COUNT(DISTINCT CASE WHEN o.status = 'paid' THEN o.seller_id END) AS paying_sellers
FROM finance.promo_orders o
JOIN finance.dim_listing l ON l.listing_id = o.listing_id
JOIN finance.dim_category c ON c.category_id = l.category_id
JOIN finance.dim_seller s ON s.seller_id = o.seller_id
GROUP BY 1, 2, 3, 4, 5, 6;

DROP TABLE IF EXISTS finance.fct_seller_month;

CREATE TABLE finance.fct_seller_month AS
SELECT
    o.seller_id,
    CAST(DATE_TRUNC('month', o.created_at) AS DATE) AS month,
    COUNT(*) AS orders_paid,
    SUM(o.amount) AS revenue
FROM finance.promo_orders o
WHERE o.status = 'paid'
GROUP BY 1, 2;

DROP TABLE IF EXISTS finance.fct_seller_retention;

CREATE TABLE finance.fct_seller_retention AS
WITH first_month AS (
    SELECT seller_id, MIN(month) AS cohort_month
    FROM finance.fct_seller_month
    GROUP BY 1
),
activity AS (
    SELECT f.cohort_month,
           (EXTRACT(YEAR FROM m.month) - EXTRACT(YEAR FROM f.cohort_month)) * 12
             + (EXTRACT(MONTH FROM m.month) - EXTRACT(MONTH FROM f.cohort_month)) AS month_number,
           m.seller_id,
           m.revenue
    FROM finance.fct_seller_month m
    JOIN first_month f ON f.seller_id = m.seller_id
),
cohort_size AS (
    SELECT cohort_month, COUNT(*) AS sellers_in_cohort
    FROM first_month
    GROUP BY 1
)
SELECT a.cohort_month,
       CAST(a.month_number AS INT) AS month_number,
       cs.sellers_in_cohort,
       COUNT(DISTINCT a.seller_id) AS active_sellers,
       CAST(COUNT(DISTINCT a.seller_id) AS FLOAT) / cs.sellers_in_cohort AS retention,
       SUM(a.revenue) AS revenue
FROM activity a
JOIN cohort_size cs ON cs.cohort_month = a.cohort_month
GROUP BY a.cohort_month, a.month_number, cs.sellers_in_cohort;
