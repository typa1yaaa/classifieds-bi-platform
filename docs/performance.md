# Производительность: до и после

Данные: `raw.events` - 52 931 093 событий за 180 дней. Медиана из 5 запусков, время выполнения на сервере; "строк" - сколько строк ClickHouse реально считал с диска. Перед сравнением проверяется, что оба варианта дают одинаковый ответ.

Файл генерируется командой `make bench` (src/bench/run_bench.py).

| Сценарий | До, мс | После, мс | Ускорение | Строк до | Строк после | Ответ совпал | Вывод | Прием |
|---|---:|---:|---:|---:|---:|:---:|---|---|
| Дневной график по категории | 44 | 11.9 | х3.7 | 6.1 млн | 219 тыс. | да | помогло | Витрина вместо сырых событий. Ответ отличается на доли процента: сырой запрос считает и повторные доставки |
| История одного объявления | 32 | 18.8 | х1.7 | 934 тыс. | 82 тыс. | да | эффекта почти нет | Проверка гипотезы «нужна проекция по listing_id». Основной ключ уже отсекает >99% строк: listing_id в нем четвертый, но префикс (дата, категория, тип) низкокардинальный, и ClickHouse применяет generic exclusion search. Проекция читает меньше строк, но быстрее не становится - место на диске она не окупает |
| Контакты без дублей доставки | 55 | 17.2 | х3.2 | 6.4 млн | 4.0 млн | да | помогло | Дедупликация один раз при сборке (ReplacingMergeTree + OPTIMIZE FINAL), а не в каждом запросе |
| Уникальные пользователи за месяц | 119 | 9.3 | х12.8 | 8.6 млн | 90 | да | помогло | Скетч uniqHLL12 в MV на зерне "день и платформа" вместо точного подсчета по сырым событиям (погрешность ~1,6%) |
| Антипример: uniq-скетчи на мелком зерне | 117 | 120.8 | **х1.0** | 8.6 млн | 1.9 млн | да | антипример | Слияние миллионов скетчей дороже, чем точный подсчет: предагрегация помогает, только если зерно подходит вопросу |
| Воронка по платформам за месяц | 42 | 8.2 | х5.1 | 8.6 млн | 540 | да | помогло | Витрина на зерне вопроса "день и платформа" (81 строка за месяц). Ответ меньше на долю дублей доставки |

## Цена оптимизаций

* Проекция `p_by_listing` занимает 439 МБ при размере таблицы 1582 МБ (вместе с проекцией) и замедляет вставку. На этих данных она не дала выигрыша, поэтому в боевой схеме ее стоит удалить (`ALTER TABLE raw.events DROP PROJECTION p_by_listing`). Оптимизацию сначала замеряют, потом оставляют.
* `uniq` против `uniqExact`: приближенный подсчет с погрешностью около 1–2% (в сценарии «Уникальные пользователи» ответы сравниваются с допуском 2%). Для финансовых метрик приближение недопустимо, для дашборда аудитории - нормально.
* Витрины и MV нужно поддерживать: MV видит только новые вставки, витрины dbt пересобираются по расписанию, а их корректность проверяют сверки в `dq.dq_checks_daily`.

## Сами запросы

### Дневной график по категории

Контакты по дням в категории «Автомобили» за 90 дней.

До:

```sql
SELECT toDate(event_time) AS d, countIf(event_type = 'contact') AS c
FROM raw.events
WHERE category_id = 101 AND event_time >= '2026-06-30 00:00:00'
GROUP BY d ORDER BY d
```

После:

```sql
SELECT event_date AS d, sum(contacts) AS c
FROM marts.fct_category_daily
WHERE category_id = 101 AND event_date >= '2026-06-30'
GROUP BY d ORDER BY d
```

### История одного объявления

Все события объявления 12345 по дням и типам.

До:

```sql
SELECT toDate(event_time) AS d, event_type, count() AS n
FROM raw.events WHERE listing_id = 12345
GROUP BY d, event_type ORDER BY d, event_type
```

После:

```sql
SELECT toDate(event_time) AS d, event_type, count() AS n
FROM raw.events WHERE listing_id = 12345
GROUP BY d, event_type ORDER BY d, event_type
```

### Контакты без дублей доставки

Число контактов за сентябрь без повторно доставленных событий.

До:

```sql
SELECT count() FROM (
SELECT event_id FROM raw.events
WHERE event_type = 'contact' AND event_date BETWEEN '2026-09-01' AND '2026-09-27'
LIMIT 1 BY event_id)
```

После:

```sql
SELECT count() FROM staging.stg_events
WHERE event_type = 'contact' AND event_date BETWEEN '2026-09-01' AND '2026-09-27'
```

### Уникальные пользователи за месяц

Сколько разных пользователей видели объявления в сентябре.

До:

```sql
SELECT uniqExact(user_id) FROM raw.events
WHERE event_date BETWEEN '2026-09-01' AND '2026-09-27'
```

После:

```sql
SELECT uniqHLL12Merge(users_hll) FROM marts.users_daily_agg
WHERE event_date BETWEEN '2026-09-01' AND '2026-09-27'
```

### Антипример: uniq-скетчи на мелком зерне

Тот же вопрос, но из агрегата "объявление и день", где скетч хранится в каждой строке.

До:

```sql
SELECT uniqExact(user_id) FROM raw.events
WHERE event_date BETWEEN '2026-09-01' AND '2026-09-27'
```

После:

```sql
SELECT uniqMerge(users_uniq) FROM marts.listing_daily_agg
WHERE event_date BETWEEN '2026-09-01' AND '2026-09-27'
```

### Воронка по платформам за месяц

Показы, просмотры и контакты по платформам за сентябрь.

До:

```sql
SELECT platform, countIf(event_type = 'impression') AS i, countIf(event_type = 'view') AS v,
countIf(event_type = 'contact') AS c
FROM raw.events WHERE event_date BETWEEN '2026-09-01' AND '2026-09-27'
GROUP BY platform ORDER BY platform
```

После:

```sql
SELECT platform, sum(impressions) AS i, sum(views) AS v, sum(contacts) AS c
FROM marts.fct_platform_daily WHERE event_date BETWEEN '2026-09-01' AND '2026-09-27'
GROUP BY platform ORDER BY platform
```
