SELECT countIf(status = 'fail') AS failed_checks
FROM dq.dq_checks_daily
WHERE check_date = (SELECT max(check_date) FROM dq.dq_checks_daily WHERE check_name != 'freshness_hours')
   OR check_name = 'freshness_hours'
