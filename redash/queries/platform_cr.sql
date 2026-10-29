SELECT event_date,
       transform(platform, ['android', 'ios', 'web'], ['Android', 'iOS', 'Web'], platform) AS platform_name,
       round(100 * cr_view_to_contact, 2) AS cr_pct
FROM marts.fct_platform_daily
WHERE event_date BETWEEN '{{ period.start }}' AND '{{ period.end }}'
ORDER BY event_date, platform_name
