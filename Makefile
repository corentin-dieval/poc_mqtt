.PHONY: install dev docker-up docker-down docker-logs test lint format publish-test live

install:
	uv sync

dev:
	uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

docker-up:
	docker compose up -d

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f backend

test:
	uv run pytest

lint:
	uv run ruff check app/

format:
	uv run ruff format app/

publish-test:
	uv run python scripts/publish_test.py

live:
	uv run python scripts/live_simulate.py
