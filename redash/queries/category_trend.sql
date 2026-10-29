SELECT event_date,
       sum(views) AS views_total,
       sum(contacts) AS contacts_total,
       round(100 * contacts_total / nullIf(views_total, 0), 2) AS cr_pct
FROM marts.fct_category_daily
WHERE event_date BETWEEN '{{ period.start }}' AND '{{ period.end }}'
  AND category_id IN ({{ category }})
  AND platform IN ({{ platform }})
GROUP BY event_date
ORDER BY event_date
