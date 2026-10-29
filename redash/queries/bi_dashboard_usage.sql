WITH views AS (
    SELECT CAST(object_id AS integer) AS dashboard_id,
           COUNT(*) AS views_30d,
           COUNT(DISTINCT user_id) AS viewers_30d,
           MAX(created_at) AS last_view_at
    FROM redash.public.events
    WHERE action = 'view'
      AND object_type = 'dashboard'
      AND created_at > current_timestamp - INTERVAL '30' DAY
    GROUP BY 1
)
SELECT d.name AS dashboard,
       COALESCE(v.views_30d, 0) AS views_30d,
       COALESCE(v.viewers_30d, 0) AS viewers_30d,
       v.last_view_at AS last_view_at,
       contains(d.tags, 'certified') AS is_certified,
       CASE WHEN COALESCE(v.views_30d, 0) < 5 THEN 'кандидат на архивацию'
            WHEN NOT contains(d.tags, 'certified') THEN 'не сертифицирован'
            ELSE 'ok' END AS verdict
FROM redash.public.dashboards AS d
LEFT JOIN views AS v ON v.dashboard_id = d.id
WHERE NOT d.is_archived
ORDER BY views_30d ASC, d.name
