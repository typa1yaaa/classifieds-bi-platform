{#- Уникальность составного ключа (зерна витрины). -#}
{% test unique_combination(model, columns) %}
SELECT {{ columns | join(', ') }}, count() AS n
FROM {{ model }}
GROUP BY {{ columns | join(', ') }}
HAVING n > 1
{% endtest %}
