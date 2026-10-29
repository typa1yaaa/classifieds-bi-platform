{#- Справочник категорий из продуктовой PostgreSQL через табличную функцию postgresql().
    Пересобирается при каждом dbt run: справочник маленький, полная перезаливка проще инкремента. -#}
{{ config(materialized='table', engine='MergeTree', order_by='category_id') }}

SELECT
    c.category_id AS category_id,
    c.name AS category_name,
    coalesce(c.parent_id, c.category_id) AS parent_category_id,
    coalesce(p.name, c.name) AS parent_category_name,
    c.is_leaf AS is_leaf
FROM {{ pg_table('categories') }} AS c
LEFT JOIN {{ pg_table('categories') }} AS p ON p.category_id = c.parent_id
