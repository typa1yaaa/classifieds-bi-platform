DROP VIEW IF EXISTS marts.mv_listing_daily;
DROP TABLE IF EXISTS marts.listing_daily_agg;

CREATE TABLE marts.listing_daily_agg
(
    event_date Date,
    category_id UInt16,
    region_id UInt16,
    platform LowCardinality(String),
    is_promoted UInt8,
    listing_id UInt32,
    impressions SimpleAggregateFunction(sum, UInt64),
    views SimpleAggregateFunction(sum, UInt64),
    contacts SimpleAggregateFunction(sum, UInt64),
    favorites SimpleAggregateFunction(sum, UInt64),
    users_uniq AggregateFunction(uniq, UInt32)
)
ENGINE = AggregatingMergeTree
PARTITION BY toYYYYMM(event_date)
ORDER BY (event_date, category_id, region_id, platform, is_promoted, listing_id);

CREATE MATERIALIZED VIEW marts.mv_listing_daily TO marts.listing_daily_agg AS
SELECT
    event_date,
    category_id,
    region_id,
    platform,
    is_promoted,
    listing_id,
    countIf(event_type = 'impression') AS impressions,
    countIf(event_type = 'view') AS views,
    countIf(event_type = 'contact') AS contacts,
    countIf(event_type = 'favorite') AS favorites,
    uniqState(user_id) AS users_uniq
FROM raw.events
GROUP BY event_date, category_id, region_id, platform, is_promoted, listing_id;

DROP VIEW IF EXISTS marts.mv_users_daily;
DROP TABLE IF EXISTS marts.users_daily_agg;

CREATE TABLE marts.users_daily_agg
(
    event_date Date,
    platform LowCardinality(String),
    users_hll AggregateFunction(uniqHLL12, UInt32)
)
ENGINE = AggregatingMergeTree
ORDER BY (event_date, platform);

CREATE MATERIALIZED VIEW marts.mv_users_daily TO marts.users_daily_agg AS
SELECT event_date, platform, uniqHLL12State(user_id) AS users_hll
FROM raw.events
GROUP BY event_date, platform;
