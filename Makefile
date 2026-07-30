.PHONY: up down logs test lint migrate bootstrap frontend-build validate

up:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f api worker

migrate:
	docker compose run --rm api alembic upgrade head

bootstrap:
	docker compose run --rm api python scripts/bootstrap_admin.py

test:
	docker compose run --rm api pytest -q

lint:
	docker compose run --rm api ruff check app tests

frontend-build:
	docker compose run --rm frontend-build

validate:
	python scripts/validate_project.py
