SELECT toStartOfWeek(event_date, 1) AS week,
       round(100 * sumIf(impressions, is_promoted = 1) / sum(impressions), 1) AS promoted_share_pct
FROM marts.fct_category_daily
WHERE event_date BETWEEN '{{ period.start }}' AND '{{ period.end }}'
GROUP BY week
ORDER BY week
