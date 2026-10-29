{#- Воронка показ - просмотр - контакт по родительским категориям и платформам. -#}
{{ config(
    materialized='table',
    engine='MergeTree',
    order_by='(event_date, parent_category_id, platform)',
    tags=['certified']
) }}

SELECT
    f.event_date AS event_date,
    c.parent_category_id AS parent_category_id,
    c.parent_category_name AS parent_category_name,
    f.platform AS platform,
    sum(f.impressions) AS impressions,
    sum(f.views) AS views,
    sum(f.contacts) AS contacts,
    views / nullIf(impressions, 0) AS ctr,
    contacts / nullIf(views, 0) AS cr_view_to_contact,
    contacts / nullIf(impressions, 0) AS cr_impression_to_contact
FROM {{ ref('fct_category_daily') }} AS f
INNER JOIN {{ ref('dim_category') }} AS c ON c.category_id = f.category_id
GROUP BY event_date, parent_category_id, parent_category_name, platform
