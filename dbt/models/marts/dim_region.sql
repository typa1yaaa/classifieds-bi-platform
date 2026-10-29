{{ config(materialized='table', engine='MergeTree', order_by='region_id') }}

SELECT
    region_id,
    name AS region_name,
    federal_district
FROM {{ pg_table('regions') }}
