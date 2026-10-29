SELECT event_date,
       events,
       baseline_median,
       status
FROM dq.dq_daily_volume
WHERE event_date BETWEEN '{{ period.start }}' AND '{{ period.end }}'
ORDER BY event_date
