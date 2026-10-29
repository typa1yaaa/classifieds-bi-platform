-include .env
export

VENV := .venv
PY := $(VENV)/bin/python
DBT := cd dbt && ../$(VENV)/bin/dbt
DWH_ENGINE ?= postgres
DWH_PROFILE := $(if $(filter vertica,$(DWH_ENGINE)),--profile vertica,)
COMPOSE := docker compose --profile core $(DWH_PROFILE) --profile fed --profile bi

.PHONY: help install up up-core down clean ping seed clickhouse dbt dwh vertica federation explain \
        redash redash-export simulate bench test lint all

help:
	@grep -E '^[a-z-]+:.*?## ' $(MAKEFILE_LIST) | awk -F':.*?## ' '{printf "  %-14s %s\n", $$1, $$2}'

$(PY):
	python3 -m venv $(VENV)
	$(PY) -m pip install --upgrade pip

install: $(PY)
	$(PY) -m pip install -r requirements.txt

up:
	$(COMPOSE) up -d

up-core:
	docker compose --profile core up -d

down:
	$(COMPOSE) down

clean:
	$(COMPOSE) down -v
	rm -rf data dbt/target

ping:
	$(PY) -m src.ping

seed:
	$(PY) -m src.generator
	$(PY) -m src.loaders.postgres

clickhouse:
	$(PY) -m src.loaders.clickhouse

dbt:
	$(DBT) build --profiles-dir . --full-refresh

dwh:
ifeq ($(DWH_ENGINE),vertica)
	$(PY) -m src.loaders.vertica
else
	$(PY) -m src.analysis.dwh_postgres $(DWH_PG_DB)
endif

vertica: dwh

federation:
	$(PY) -m src.loaders.trino

explain:
	$(PY) -m src.loaders.trino explain

redash:
	$(PY) -m src.redash_sync.apply

redash-export:
	$(PY) -m src.redash_sync.export

simulate:
	$(PY) -m src.redash_sync.simulate_activity

bench:
	$(PY) -m src.bench.run_bench

test:
	$(PY) -m pytest -q tests

lint:
	$(PY) -m pytest -q tests/test_sql_syntax.py

all: seed clickhouse dbt dwh federation
