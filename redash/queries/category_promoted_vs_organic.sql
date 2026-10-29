SELECT event_date,
       if(is_promoted = 1, 'Продвижение', 'Органика') AS traffic,
       sum(contacts) AS contacts_total
FROM marts.fct_category_daily
WHERE event_date BETWEEN '{{ period.start }}' AND '{{ period.end }}'
  AND category_id IN ({{ category }})
  AND platform IN ({{ platform }})
GROUP BY event_date, traffic
ORDER BY event_date, traffic
