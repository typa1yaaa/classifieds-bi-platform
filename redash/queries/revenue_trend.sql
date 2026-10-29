SELECT order_date,
       CASE service_type WHEN 'bump' THEN 'Поднятие' WHEN 'highlight' THEN 'Выделение'
                         WHEN 'premium' THEN 'Премиум' ELSE service_type END AS service,
       SUM(revenue) AS revenue
FROM finance.fct_promo_revenue_daily
WHERE order_date BETWEEN '{{ period.start }}' AND '{{ period.end }}'
GROUP BY 1, 2
ORDER BY 1, 2
