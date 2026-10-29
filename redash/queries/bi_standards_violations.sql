SELECT q.name AS query,
       u.name AS owner,
       CASE WHEN regexp_like(q.query, '\braw\.') THEN 'читает raw.*'
            WHEN regexp_like(q.query, '\bstaging\.') THEN 'читает staging.*'
       END AS violation,
       q.updated_at AS updated_at
FROM redash.public.queries AS q
JOIN redash.public.users AS u ON u.id = q.user_id
WHERE NOT q.is_archived
  AND NOT contains(q.tags, 'governance')
  AND (regexp_like(q.query, '\braw\.') OR regexp_like(q.query, '\bstaging\.'))
ORDER BY q.updated_at DESC
