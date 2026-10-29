SELECT category_id, toDate(event_time) AS d, countIf(event_type = 'contact') AS contacts
FROM raw.events
WHERE toDate(event_time) >= today() - 30
GROUP BY category_id, d
ORDER BY d, category_id
