.PHONY: help install install-api install-web dev api web test test-api test-web lint typecheck format build docker-up docker-down screenshots samples agents-demo qgis-plugin clean

PY ?= python3
PIP ?= $(PY) -m pip

help:
	@echo "CarbonCreditBuy — common tasks"
	@echo "  make install      install Python packages (editable) and web dependencies"
	@echo "  make dev          run API (8000) and web (5173) together"
	@echo "  make api          run the FastAPI server with reload"
	@echo "  make web          run the Vite dev server"
	@echo "  make test         pytest + vitest + typecheck"
	@echo "  make lint         ruff + mypy + eslint"
	@echo "  make build        production web build + Python wheels"
	@echo "  make docker-up    docker compose (api, web, postgis, minio)"
	@echo "  make agents-demo  print a full AI-agent run for the demo plot"
	@echo "  make samples      regenerate sample API responses and demo fixtures"
	@echo "  make screenshots  capture docs screenshots (API + web preview running)"
	@echo "  make qgis-plugin  build the QGIS plugin zip"

install: install-api install-web

install-api:
	$(PIP) install -r requirements.txt
	$(PIP) install -e packages/carbon-engine -e packages/geo-engine -e packages/policy-engine -e packages/report-engine -e packages/agent-framework -e integrations -e apps/api

install-web:
	cd apps/web && npm install

api:
	cd apps/api && $(PY) -m uvicorn app.main:app --reload --host $${ATLAS_API_HOST:-0.0.0.0} --port $${ATLAS_API_PORT:-8000}

web:
	cd apps/web && npm run dev

dev:
	@trap 'kill 0' INT; $(MAKE) api & $(MAKE) web & wait

test: test-api test-web

test-api:
	$(PY) -m pytest -q

test-web:
	cd apps/web && npm run typecheck && npm run test -- --run

lint:
	$(PY) -m ruff check .
	$(PY) -m mypy packages apps/api/app integrations --ignore-missing-imports
	cd apps/web && npm run lint

format:
	$(PY) -m ruff format .
	cd apps/web && npm run format

typecheck:
	cd apps/web && npm run typecheck

build:
	cd apps/web && npm run build

docker-up:
	docker compose up --build

docker-down:
	docker compose down -v

screenshots:
	node scripts/capture_screenshots.mjs

samples:
	$(PY) scripts/make_sample_responses.py
	$(PY) scripts/make_sample_tree_age.py
	$(PY) scripts/make_sample_imports.py
	cd apps/web && npm run fixtures:demo

agents-demo:
	$(PY) examples/agents/run_team.py

qgis-plugin:
	$(MAKE) -C integrations/qgis-plugin package

clean:
	rm -rf .cache .reports apps/web/dist .pytest_cache .mypy_cache .ruff_cache
	find . -name "__pycache__" -type d -prune -exec rm -rf {} +
