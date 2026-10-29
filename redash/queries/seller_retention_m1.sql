SELECT TO_CHAR(cohort_month, 'YYYY-MM') AS cohort,
       sellers_in_cohort,
       ROUND(CAST(100 * retention AS NUMERIC), 1) AS retention_m1_pct
FROM finance.fct_seller_retention
WHERE month_number = 1
ORDER BY cohort_month
