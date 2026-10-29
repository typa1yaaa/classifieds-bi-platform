SELECT dictGet('marts.dict_categories', 'name', toUInt64(parent_category_id)) AS category,
       transform(service_type, ['bump', 'highlight', 'premium'], ['Поднятие', 'Выделение', 'Премиум'],
                 service_type) AS service,
       countIf(is_eligible = 1) AS orders,
       round(sumIf(amount, is_eligible = 1)
             / nullIf(sumIf(extra_contacts, is_eligible = 1), 0)) AS cost_per_extra_contact_rub
FROM marts.promo_order_effect
WHERE promo_start_date BETWEEN '{{ period.start }}' AND '{{ period.end }}'
GROUP BY category, service
HAVING orders >= 30
ORDER BY category, service
