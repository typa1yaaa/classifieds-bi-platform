{#-
  Аномалии объема: событий за день сравниваются с медианой того же дня недели
  за 4 предыдущие недели. Сравнение с тем же днем недели убирает недельную сезонность
  (в выходные трафик выше на 10–15%), медиана устойчива к прошлым инцидентам.
-#}
{{ config(materialized='table', engine='MergeTree', order_by='event_date') }}

WITH daily AS (
    SELECT toDate(event_time) AS event_date, count() AS events
    FROM {{ source('raw', 'events') }}
    GROUP BY event_date
)
SELECT
    event_date,
    events,
    median(events) OVER w AS baseline_median,
    count() OVER w AS history_weeks,
    events / nullIf(baseline_median, 0) - 1 AS deviation,
    multiIf(history_weeks < 2, 'insufficient_history',
            abs(deviation) > 0.10, 'fail',
            abs(deviation) > 0.06, 'warn', 
            'pass') AS status
FROM daily
WINDOW w AS (PARTITION BY toDayOfWeek(event_date) ORDER BY event_date
             ROWS BETWEEN 4 PRECEDING AND 1 PRECEDING)
