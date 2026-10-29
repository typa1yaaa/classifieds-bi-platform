SELECT q.name AS query,
       ds.name AS data_source,
       COUNT(*) AS runs,
       ROUND(AVG(r.runtime), 2) AS avg_runtime_s,
       ROUND(MAX(r.runtime), 2) AS max_runtime_s
FROM redash.public.query_results AS r
JOIN redash.public.queries AS q ON q.query_hash = r.query_hash
JOIN redash.public.data_sources AS ds ON ds.id = r.data_source_id
WHERE NOT q.is_archived
GROUP BY 1, 2
ORDER BY avg_runtime_s DESC
LIMIT 20
