{#-
  Дедупликация повторных доставок через ReplacingMergeTree.

  Строки с одинаковым ключом сортировки схлопываются при слиянии кусков, остается версия
  с максимальным ingested_at. Слияния фоновые и не гарантированы, поэтому после сборки
  принудительно делаем OPTIMIZE ... FINAL: модель пересобирается батчем, и платить за FINAL
  один раз при сборке дешевле, чем в каждом запросе дашборда.

  event_id стоит последним в ключе: дубли одного события всегда совпадают по дате, категории,
  типу и объявлению, поэтому оказываются рядом, а префикс ключа совпадает с raw.events
  и сохраняет быстрые фильтры по дате и категории.
-#}
{{ config(
    materialized='table',
    engine='ReplacingMergeTree(ingested_at)',
    order_by='(event_date, category_id, event_type, listing_id, event_id)',
    partition_by='toYYYYMM(event_date)',
    post_hook=["OPTIMIZE TABLE {{ this }} FINAL"]
) }}

SELECT
    event_id,
    event_time,
    toDate(event_time) AS event_date,
    event_type,
    user_id,
    listing_id,
    seller_id,
    category_id,
    region_id,
    platform,
    is_promoted,
    promo_service,
    ingested_at
FROM {{ source('raw', 'events') }}
WHERE event_type IN ('impression', 'view', 'contact', 'favorite')
