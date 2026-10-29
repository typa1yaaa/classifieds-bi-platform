{#- Табличная функция ClickHouse для чтения таблицы из продуктовой PostgreSQL.
    Хост - как его видит сервер ClickHouse (в docker-сети это "postgres"). -#}
{% macro pg_table(table, schema='public') -%}
postgresql(
    '{{ env_var("PG_HOST_FOR_CH", env_var("PG_HOST", "localhost")) }}:{{ env_var("PG_PORT", "5432") }}',
    '{{ env_var("PG_DB", "marketplace") }}', '{{ table }}',
    '{{ env_var("PG_USER", "bi") }}', '{{ env_var("PG_PASSWORD", "bi") }}', '{{ schema }}'
)
{%- endmacro %}
