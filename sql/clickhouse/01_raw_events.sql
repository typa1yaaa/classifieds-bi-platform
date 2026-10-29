DROP TABLE IF EXISTS raw.events;

CREATE TABLE raw.events
(
    event_id UInt64, -- ключ события; повторная доставка = тот же event_id
    event_time DateTime('UTC'),
    event_date Date DEFAULT toDate(event_time),
    event_type LowCardinality(String), -- impression / view / contact / favorite
    user_id UInt32,
    listing_id UInt32,
    seller_id UInt32,
    category_id UInt16,
    region_id UInt16,
    platform LowCardinality(String), -- android / ios / web
    is_promoted UInt8,
    promo_service LowCardinality(String), -- '' если объявление не продвигалось в этот день
    ingested_at DateTime('UTC') -- время доставки в хранилище
)
ENGINE = MergeTree
PARTITION BY toYYYYMM(event_date)
ORDER BY (event_date, category_id, event_type, listing_id);
