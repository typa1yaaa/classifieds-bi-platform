WITH (SELECT max(event_date) FROM marts.fct_platform_daily) AS last_day
SELECT platform_name,
       round(100 * cr_last, 2) AS cr_last_3d_pct,
       round(100 * cr_base, 2) AS cr_baseline_28d_pct,
       round(cr_last / cr_base, 3) AS ratio
FROM (
    SELECT transform(platform, ['android', 'ios', 'web'], ['Android', 'iOS', 'Web'], platform) AS platform_name,
           sumIf(contacts, event_date > last_day - 3) / sumIf(views, event_date > last_day - 3) AS cr_last,
           sumIf(contacts, event_date BETWEEN last_day - 30 AND last_day - 3)
             / sumIf(views, event_date BETWEEN last_day - 30 AND last_day - 3) AS cr_base
    FROM marts.fct_platform_daily
    GROUP BY platform_name
)
ORDER BY ratio
