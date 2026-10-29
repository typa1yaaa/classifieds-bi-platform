SELECT TO_CHAR(cohort_month, 'YYYY-MM') AS cohort,
       month_number,
       sellers_in_cohort,
       active_sellers,
       ROUND(CAST(100 * retention AS NUMERIC), 1) AS retention_pct
FROM finance.fct_seller_retention
ORDER BY cohort_month, month_number
