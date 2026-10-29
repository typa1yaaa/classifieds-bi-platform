{#- В ClickHouse «схема» dbt = база данных. Используем имя из +schema как есть
    (staging / marts / dq), без префикса target-схемы. -#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
