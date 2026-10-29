SELECT check_name,
       max(check_date) AS last_date,
       argMax(status, check_date) AS last_status,
       round(argMax(value, check_date), 4) AS last_value,
       argMax(threshold, check_date) AS last_threshold,
       countIf(status = 'fail') AS fails_total
FROM dq.dq_checks_daily
GROUP BY check_name
ORDER BY fails_total DESC, check_name
