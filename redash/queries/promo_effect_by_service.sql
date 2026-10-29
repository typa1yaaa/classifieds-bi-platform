WITH honest AS (
    SELECT service_type,
           countIf(is_eligible = 1) AS orders_evaluated,
           sumIf(contacts_per_day_promo, is_eligible = 1)
             / sumIf(contacts_per_day_before, is_eligible = 1) AS uplift_before_after,
           sumIf(extra_contacts, is_eligible = 1) AS extra_contacts_total,
           sumIf(amount, is_eligible = 1) / nullIf(sumIf(extra_contacts, is_eligible = 1), 0) AS cost_per_extra_contact
    FROM marts.promo_order_effect
    WHERE promo_start_date BETWEEN '{{ period.start }}' AND '{{ period.end }}'
    GROUP BY service_type
),
naive AS (
    SELECT promo_service AS service_type,
           avg(contacts) / (SELECT avg(contacts) FROM marts.fct_listing_daily
                            WHERE is_promoted = 0
                              AND event_date BETWEEN '{{ period.start }}' AND '{{ period.end }}') AS uplift_naive
    FROM marts.fct_listing_daily
    WHERE is_promoted = 1 AND event_date BETWEEN '{{ period.start }}' AND '{{ period.end }}'
    GROUP BY promo_service
)
SELECT transform(h.service_type, ['bump', 'highlight', 'premium'], ['Поднятие', 'Выделение', 'Премиум'],
                 h.service_type) AS service,
       h.orders_evaluated AS orders_evaluated,
       round(n.uplift_naive, 2) AS uplift_naive,
       round(h.uplift_before_after, 2) AS uplift_before_after,
       round(h.extra_contacts_total) AS extra_contacts,
       round(h.cost_per_extra_contact) AS cost_per_extra_contact_rub
FROM honest AS h
LEFT JOIN naive AS n ON n.service_type = h.service_type
ORDER BY uplift_before_after DESC
