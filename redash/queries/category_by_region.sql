SELECT region, views_total, contacts_total, cr_pct
FROM (
    SELECT dictGet('marts.dict_regions', 'name', toUInt64(region_id)) AS region,
           sum(views) AS views_total,
           sum(contacts) AS contacts_total,
           round(100 * contacts_total / nullIf(views_total, 0), 2) AS cr_pct
    FROM marts.fct_category_daily
    WHERE event_date BETWEEN '{{ period.start }}' AND '{{ period.end }}'
      AND category_id IN ({{ category }})
      AND platform IN ({{ platform }})
    GROUP BY region
    ORDER BY contacts_total DESC
    LIMIT 15
)
ORDER BY contacts_total ASC
