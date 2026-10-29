{#-
  Сертифицированная витрина "объявление и день". Простые типы - читается из Trino и Redash.

  Инкремент: insert_overwrite по месячным партициям. При каждом запуске пересчитываются
  партиции, в которые попадают последние lookback_days дней (поздние события, дубли),
  и подменяются целиком через REPLACE PARTITION. Это атомарно и не требует мутаций
  (DELETE в ClickHouse дорогой), в отличие от delete+insert.
-#}
{{ config(
    materialized='incremental',
    incremental_strategy='insert_overwrite',
    engine='MergeTree',
    partition_by='toYYYYMM(event_date)',
    order_by='(event_date, category_id, listing_id)',
    tags=['certified']
) }}

SELECT
    event_date,
    listing_id,
    any(seller_id) AS seller_id,
    any(category_id) AS category_id,
    any(region_id) AS region_id,
    max(is_promoted) AS is_promoted,
    anyIf(promo_service, promo_service != '') AS promo_service,
    countIf(event_type = 'impression') AS impressions,
    countIf(event_type = 'view') AS views,
    countIf(event_type = 'contact') AS contacts,
    countIf(event_type = 'favorite') AS favorites,
    uniqExact(user_id) AS unique_users
FROM {{ ref('stg_events') }}
{% if is_incremental() %}
WHERE event_date >= toStartOfMonth(
    (SELECT max(event_date) FROM {{ this }}) - toIntervalDay({{ var('lookback_days') }}))
{% endif %}
GROUP BY event_date, listing_id
