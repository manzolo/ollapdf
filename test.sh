#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# Start services
echo "Creating docker network..."
docker network create ollapdf-net || true

echo "Starting services..."
docker compose -f docker-compose.yml -f docker-compose.cpu.yml up -d --build

# Wait for the Streamlit app to be ready
echo "Waiting for Streamlit app..."
./wait-for-it.sh localhost:8501 --timeout=60

# Perform a health check
echo "Performing health check..."
curl -f http://localhost:8501

# Stop services
echo "Stopping services..."
docker compose -f docker-compose.yml -f docker-compose.cpu.yml down

echo "Removing docker network..."
docker network rm ollapdf-net || true
