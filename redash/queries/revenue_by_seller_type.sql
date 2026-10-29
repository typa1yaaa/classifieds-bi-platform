SELECT CASE seller_type WHEN 'company' THEN 'Компании' ELSE 'Частные' END AS seller_type,
       CASE service_type WHEN 'bump' THEN 'Поднятие' WHEN 'highlight' THEN 'Выделение'
                         WHEN 'premium' THEN 'Премиум' ELSE service_type END AS service,
       ROUND(SUM(revenue)) AS revenue,
       ROUND(SUM(revenue) / NULLIF(SUM(orders_paid), 0)) AS avg_order_value
FROM finance.fct_promo_revenue_daily
WHERE order_date BETWEEN '{{ period.start }}' AND '{{ period.end }}'
GROUP BY 1, 2
ORDER BY 1, 2
