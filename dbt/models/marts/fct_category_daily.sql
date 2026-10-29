{#- Витрина для обзорных и self-service дашбордов: день, категория, регион, платформа, продвижение.
    Все метрики аддитивны - можно суммировать по любому подмножеству измерений.
    Уникальных пользователей здесь нет намеренно: они не суммируются (см. fct_platform_daily). -#}
{{ config(
    materialized='table',
    engine='MergeTree',
    partition_by='toYYYYMM(event_date)',
    order_by='(event_date, category_id, region_id, platform, is_promoted)',
    tags=['certified']
) }}

SELECT
    event_date,
    category_id,
    region_id,
    platform,
    is_promoted,
    countIf(event_type = 'impression') AS impressions,
    countIf(event_type = 'view') AS views,
    countIf(event_type = 'contact') AS contacts,
    countIf(event_type = 'favorite') AS favorites
FROM {{ ref('stg_events') }}
GROUP BY event_date, category_id, region_id, platform, is_promoted
