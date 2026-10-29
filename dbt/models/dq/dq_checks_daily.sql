{#-
  Единый журнал проверок качества данных: одна строка = проверка и дата.
  На нем строятся дашборд Data Quality и алерт Redash (статус fail за последние сутки).
-#}
{{ config(materialized='table', engine='MergeTree', order_by='(check_name, check_date)') }}

SELECT
    'volume_vs_same_weekday' AS check_name,
    event_date AS check_date,
    toFloat64(deviation) AS value,
    0.10 AS threshold,
    status,
    concat('events=', toString(events), ', baseline=', toString(baseline_median)) AS details
FROM {{ ref('dq_daily_volume') }}

UNION ALL

SELECT
    'duplicate_share',
    r.d,
    (r.cnt - s.cnt) / r.cnt,
    0.01,
    if((r.cnt - s.cnt) / r.cnt > 0.01, 'fail', 'pass'),
    concat('raw=', toString(r.cnt), ', dedup=', toString(s.cnt))
FROM (SELECT toDate(event_time) AS d, count() AS cnt FROM {{ source('raw', 'events') }} GROUP BY d) AS r
INNER JOIN (SELECT event_date AS d, count() AS cnt FROM {{ ref('stg_events') }} GROUP BY d) AS s ON s.d = r.d

UNION ALL

SELECT
    'stg_vs_mart_views',
    s.d,
    toFloat64(s.views) - toFloat64(m.views),
    0,
    if(s.views = m.views, 'pass', 'fail'),
    concat('stg=', toString(s.views), ', mart=', toString(m.views))
FROM (SELECT event_date AS d, countIf(event_type = 'view') AS views FROM {{ ref('stg_events') }} GROUP BY d) AS s
LEFT JOIN (SELECT event_date AS d, sum(views) AS views FROM {{ ref('fct_listing_daily') }} GROUP BY d) AS m ON m.d = s.d

UNION ALL

SELECT
    'contacts_gt_views',
    event_date,
    toFloat64(countIf(contacts > views)),
    0,
    if(countIf(contacts > views) = 0, 'pass', 'fail'),
    'listing-days with contacts > views'
FROM {{ ref('fct_listing_daily') }}
GROUP BY event_date

UNION ALL

SELECT
    'freshness_hours',
    toDate('{{ var("as_of_date") }}'),
    toFloat64(dateDiff('hour', max(event_time), toDateTime('{{ var("as_of_date") }} 00:00:00', 'UTC'))),
    24,
    if(dateDiff('hour', max(event_time), toDateTime('{{ var("as_of_date") }} 00:00:00', 'UTC')) > 24, 'fail', 'pass'),
    concat('last_event=', toString(max(event_time)))
FROM {{ source('raw', 'events') }}
