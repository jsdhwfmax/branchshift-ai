.PHONY: install dev api-dev web-dev test lint build check

install:
	python3.13 -m venv .venv
	.venv/bin/python -m pip install -U pip
	.venv/bin/python -m pip install -e 'services/api[dev,contree]'
	python3.13 -m venv fixtures/pydantic-v1-app/.venv
	fixtures/pydantic-v1-app/.venv/bin/python -m pip install -e 'fixtures/pydantic-v1-app[test]'
	pnpm install

api-dev:
	.venv/bin/uvicorn app.main:app --reload --app-dir services/api --port 8000

web-dev:
	pnpm --dir apps/web dev

dev:
	@echo "Run 'make api-dev' and 'make web-dev' in separate terminals."

test:
	.venv/bin/pytest services/api/tests -q
	fixtures/pydantic-v1-app/.venv/bin/pytest fixtures/pydantic-v1-app/tests -q
	pnpm --dir apps/web exec vitest run

lint:
	.venv/bin/ruff check services/api/app services/api/tests
	.venv/bin/python -m mypy services/api/app
	pnpm --dir apps/web lint

build:
	pnpm --dir apps/web build

check: lint test build
