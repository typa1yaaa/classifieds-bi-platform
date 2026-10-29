CREATE TABLE IF NOT EXISTS marts.promo_order_effect
(
    order_id UInt32,
    listing_id UInt32,
    seller_id UInt32,
    category_id UInt16,
    parent_category_id UInt16,
    region_id UInt16,
    service_type LowCardinality(String),
    amount Decimal(12, 2),
    promo_start_date Date,
    promo_days UInt16,
    contacts_promo UInt32,
    contacts_before UInt32,
    impressions_promo UInt32,
    impressions_before UInt32,
    contacts_per_day_promo Float64,
    contacts_per_day_before Float64,
    extra_contacts Float64,
    is_eligible UInt8,
    calculated_at DateTime DEFAULT now()
)
ENGINE = MergeTree
ORDER BY (promo_start_date, parent_category_id, order_id);
