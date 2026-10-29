SELECT check_date, check_name, status, round(value, 4) AS value, threshold, details
FROM dq.dq_checks_daily
WHERE status IN ('fail', 'warn')
ORDER BY check_date DESC, check_name
