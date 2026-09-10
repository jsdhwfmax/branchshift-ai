.PHONY: install dev api-dev web-dev test lint build check

PYTHON ?= python3.13
API_VENV ?= .venv
FIXTURE_VENV ?= fixtures/pydantic-v1-app/.venv

install:
	$(PYTHON) -m venv $(API_VENV)
	$(API_VENV)/bin/python -m pip install -U pip
	$(API_VENV)/bin/python -m pip install -e 'services/api[dev,contree]'
	$(PYTHON) -m venv $(FIXTURE_VENV)
	$(FIXTURE_VENV)/bin/python -m pip install -e 'fixtures/pydantic-v1-app[test]'
	pnpm install

api-dev:
	$(API_VENV)/bin/uvicorn app.main:app --reload --app-dir services/api --port 8000

web-dev:
	pnpm --dir apps/web dev

dev:
	@echo "Run 'make api-dev' and 'make web-dev' in separate terminals."

test:
	$(API_VENV)/bin/python -m pytest services/api/tests -q
	$(FIXTURE_VENV)/bin/python -m pytest fixtures/pydantic-v1-app/tests -q
	pnpm --dir apps/web exec vitest run

lint:
	$(API_VENV)/bin/ruff check services/api/app services/api/tests
	$(API_VENV)/bin/python -m mypy services/api/app
	pnpm --dir apps/web lint

build:
	pnpm --dir apps/web build

check: lint test build
