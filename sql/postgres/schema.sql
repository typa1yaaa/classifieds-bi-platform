DROP TABLE IF EXISTS public.users;
DROP TABLE IF EXISTS public.listings;
DROP TABLE IF EXISTS public.sellers;
DROP TABLE IF EXISTS public.regions;
DROP TABLE IF EXISTS public.categories;

CREATE TABLE public.categories (
    category_id integer PRIMARY KEY,
    parent_id integer REFERENCES public.categories (category_id),
    name text NOT NULL,
    is_leaf boolean NOT NULL
);

CREATE TABLE public.regions (
    region_id integer PRIMARY KEY,
    name text NOT NULL,
    federal_district text NOT NULL,
    population_weight numeric(6, 2) NOT NULL
);

CREATE TABLE public.sellers (
    seller_id integer PRIMARY KEY,
    seller_type text NOT NULL CHECK (seller_type IN ('private', 'company')),
    region_id integer NOT NULL REFERENCES public.regions (region_id),
    registered_at timestamp NOT NULL
);

CREATE TABLE public.listings (
    listing_id integer PRIMARY KEY,
    seller_id integer NOT NULL REFERENCES public.sellers (seller_id),
    category_id integer NOT NULL REFERENCES public.categories (category_id),
    region_id integer NOT NULL REFERENCES public.regions (region_id),
    price numeric(14, 2) NOT NULL,
    created_at timestamp NOT NULL,
    closed_at timestamp,
    status text NOT NULL CHECK (status IN ('active', 'sold', 'archived'))
);

CREATE TABLE public.users (
    user_id integer PRIMARY KEY,
    region_id integer NOT NULL REFERENCES public.regions (region_id),
    registered_at timestamp NOT NULL
);

CREATE INDEX listings_seller_idx ON public.listings (seller_id);
CREATE INDEX listings_category_idx ON public.listings (category_id);
