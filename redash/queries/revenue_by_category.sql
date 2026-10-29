SELECT c.name AS category,
       SUM(f.revenue) AS revenue,
       SUM(f.orders_paid) AS orders,
       SUM(f.revenue) / SUM(SUM(f.revenue)) OVER () AS share
FROM finance.fct_promo_revenue_daily AS f
JOIN finance.dim_category AS c ON c.category_id = f.parent_category_id
WHERE f.order_date BETWEEN '{{ period.start }}' AND '{{ period.end }}'
GROUP BY c.name
ORDER BY revenue ASC
