SELECT CAST(e.created_at AS date) AS day,
       d.name AS dashboard,
       COUNT(*) AS views
FROM redash.public.events AS e
JOIN redash.public.dashboards AS d ON d.id = CAST(e.object_id AS integer)
WHERE e.action = 'view' AND e.object_type = 'dashboard'
  AND e.created_at > current_timestamp - INTERVAL '30' DAY
GROUP BY 1, 2
ORDER BY 1, 2
