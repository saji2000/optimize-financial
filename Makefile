.PHONY: dev build test lint backend frontend worker

dev:
	docker compose up --build

build:
	docker compose build

test:
	cd backend && pytest

lint:
	cd backend && ruff check app tests
	cd frontend && npm run lint

backend:
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

worker:
	cd backend && celery -A app.workers.celery_app.celery_app worker --loglevel=INFO

frontend:
	cd frontend && npm run dev -- --host 0.0.0.0

