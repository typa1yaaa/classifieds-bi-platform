SELECT category_name AS name, category_id AS value
FROM marts.dim_category
WHERE is_leaf
ORDER BY parent_category_name, category_name
