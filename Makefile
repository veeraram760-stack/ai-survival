.PHONY: install test lint format run dev deploy clean

install:
	pip install -r requirements.txt
	cd dashboard && npm install

test:
	pytest tests/ -v --cov=backend --cov-report=html

lint:
	ruff check backend/ tests/
	cd dashboard && npm run lint

format:
	ruff format backend/ tests/

run:
	uvicorn backend.main:app --reload --port 8000

dev:
	docker compose up -d
	cd dashboard && npm run dev

deploy:
	bash deploy.sh

clean:
	docker compose down -v
	rm -rf __pycache__ .pytest_cache htmlcov
