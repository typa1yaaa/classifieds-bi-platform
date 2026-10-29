{#- Любая проверка качества в статусе fail поднимает предупреждение в dbt build.
    На синтетических данных ожидаемо срабатывает на заложенный инцидент с потерей батча. -#}
{{ config(severity='warn', tags=['dq']) }}

SELECT check_name, check_date, value, threshold, details
FROM {{ ref('dq_checks_daily') }}
WHERE status = 'fail'
