#!/bin/bash
set -e

echo "Deploying AI Survival System..."

# Check prerequisites
command -v docker >/dev/null 2>&1 || { echo "Docker is required but not installed."; exit 1; }
command -v docker compose >/dev/null 2>&1 || { echo "Docker Compose is required but not installed."; exit 1; }

# Create .env if it doesn't exist
if [ ! -f .env ]; then
    cp .env.example .env
    echo "Created .env file from .env.example. Please edit with your API keys."
fi

# Build and start services
docker compose down -v
docker compose build
docker compose up -d postgres redis

echo "Waiting for database..."
sleep 10

# Run database migrations
docker compose run --rm backend alembic upgrade head || true

# Start all services
docker compose up -d

echo "AI Survival System deployed!"
echo "Dashboard: http://localhost:3000"
echo "API: http://localhost:8000"
