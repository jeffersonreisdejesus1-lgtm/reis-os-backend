.PHONY: install run test lint format typecheck quality up down migrate

install:
	pip install -e ".[dev]"

run:
	uvicorn app.main:app --reload

test:
	pytest

lint:
	ruff check .

format:
	ruff format .

typecheck:
	mypy app tests

quality: lint typecheck test

up:
	docker compose up --build

down:
	docker compose down

migrate:
	alembic upgrade head
