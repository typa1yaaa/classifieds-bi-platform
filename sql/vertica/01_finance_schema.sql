CREATE SCHEMA IF NOT EXISTS finance;

DROP TABLE IF EXISTS finance.promo_orders_stg CASCADE;
DROP TABLE IF EXISTS finance.promo_orders_rejected CASCADE;
DROP TABLE IF EXISTS finance.promo_orders_quarantine CASCADE;
DROP TABLE IF EXISTS finance.promo_orders CASCADE;
DROP TABLE IF EXISTS finance.dim_listing CASCADE;
DROP TABLE IF EXISTS finance.dim_seller CASCADE;
DROP TABLE IF EXISTS finance.dim_region CASCADE;
DROP TABLE IF EXISTS finance.dim_category CASCADE;

CREATE TABLE finance.promo_orders_stg
(
    order_id INT,
    listing_id INT,
    seller_id INT,
    service_type VARCHAR(32),
    created_at TIMESTAMP,
    amount NUMERIC(12, 2),
    status VARCHAR(16),
    active_from TIMESTAMP,
    active_to TIMESTAMP
);

CREATE TABLE finance.promo_orders
(
    order_id INT NOT NULL PRIMARY KEY,
    listing_id INT NOT NULL,
    seller_id INT NOT NULL,
    service_type VARCHAR(32) NOT NULL,
    created_at    TIMESTAMP NOT NULL,
    amount NUMERIC(12, 2) NOT NULL,
    status VARCHAR(16) NOT NULL,
    active_from TIMESTAMP,
    active_to TIMESTAMP
)

ORDER BY created_at, seller_id
SEGMENTED BY HASH(order_id) ALL NODES;

CREATE TABLE finance.promo_orders_quarantine
(
    order_id INT,
    listing_id INT,
    seller_id INT,
    service_type VARCHAR(32),
    created_at TIMESTAMP,
    amount NUMERIC(12, 2),
    status VARCHAR(16),
    reason VARCHAR(64),
    quarantined_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE finance.dim_category
(
    category_id INT NOT NULL PRIMARY KEY,
    parent_id INT,
    name VARCHAR(256) NOT NULL,
    is_leaf BOOLEAN NOT NULL
)
UNSEGMENTED ALL NODES;

CREATE TABLE finance.dim_region
(
    region_id INT NOT NULL PRIMARY KEY,
    name VARCHAR(256) NOT NULL,
    federal_district VARCHAR(256) NOT NULL,
    population_weight NUMERIC(6, 2)
)
UNSEGMENTED ALL NODES;

CREATE TABLE finance.dim_seller
(
    seller_id INT NOT NULL PRIMARY KEY,
    seller_type VARCHAR(16) NOT NULL,
    region_id INT NOT NULL,
    registered_at TIMESTAMP NOT NULL
)
UNSEGMENTED ALL NODES;

CREATE TABLE finance.dim_listing
(
    listing_id INT NOT NULL PRIMARY KEY,
    seller_id INT NOT NULL,
    category_id INT NOT NULL,
    region_id INT NOT NULL,
    price NUMERIC(14, 2),
    created_at TIMESTAMP NOT NULL,
    closed_at TIMESTAMP,
    status VARCHAR(16) NOT NULL
)
ORDER BY listing_id
SEGMENTED BY HASH(listing_id) ALL NODES;
