DROP DICTIONARY IF EXISTS marts.dict_categories;
DROP DICTIONARY IF EXISTS marts.dict_regions;

CREATE DICTIONARY marts.dict_categories
(
    category_id UInt64,
    parent_id UInt64,
    name String,
    is_leaf UInt8
)
PRIMARY KEY category_id
SOURCE(POSTGRESQL(
    host '{pg_host}' port {pg_port} db '{pg_db}' user '{pg_user}' password '{pg_password}'
    query 'SELECT category_id, coalesce(parent_id, 0) AS parent_id, name, is_leaf::int AS is_leaf FROM public.categories'
))
LAYOUT(FLAT())
LIFETIME(MIN 300 MAX 600);

CREATE DICTIONARY marts.dict_regions
(
    region_id         UInt64,
    name              String,
    federal_district  String
)
PRIMARY KEY region_id
SOURCE(POSTGRESQL(
    host '{pg_host}' port {pg_port} db '{pg_db}' user '{pg_user}' password '{pg_password}'
    table 'regions'
))
LAYOUT(FLAT())
LIFETIME(MIN 300 MAX 600);
