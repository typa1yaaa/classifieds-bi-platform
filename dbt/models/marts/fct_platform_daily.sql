{#- День и платформа: аудитория и конверсии. Основа бизнес-мониторинга (алерт на CR по платформам).
    dau и contact_users - точные уникальные (uniqExact) на этом зерне, суммировать по дням нельзя. -#}
{{ config(
    materialized='table',
    engine='MergeTree',
    order_by='(event_date, platform)',
    tags=['certified']
) }}

SELECT
    event_date,
    platform,
    uniqExact(user_id) AS dau,
    uniqExactIf(user_id, event_type = 'contact') AS contact_users,
    countIf(event_type = 'impression') AS impressions,
    countIf(event_type = 'view') AS views,
    countIf(event_type = 'contact') AS contacts,
    views / nullIf(impressions, 0) AS ctr,
    contacts / nullIf(views, 0) AS cr_view_to_contact
FROM {{ ref('stg_events') }}
GROUP BY event_date, platform
