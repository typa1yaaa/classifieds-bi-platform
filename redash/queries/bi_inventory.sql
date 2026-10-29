SELECT 'dashboards' AS object_type,
       COUNT(*) AS total,
       COUNT_IF(contains(tags, 'certified')) AS certified,
       ROUND(CAST(COUNT_IF(contains(tags, 'certified')) AS double) / COUNT(*), 2) AS certified_share
FROM redash.public.dashboards WHERE NOT is_archived
UNION ALL
SELECT 'queries', COUNT(*), COUNT_IF(contains(tags, 'certified')),
       ROUND(CAST(COUNT_IF(contains(tags, 'certified')) AS double) / COUNT(*), 2)
FROM redash.public.queries WHERE NOT is_archived
