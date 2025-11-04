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
echo "Giving Streamlit app more time to initialize..."
sleep 30

# Debugging: Print logs if health check fails
set +e
echo "--- OllaPDF Container Logs (before health check) ---"
docker logs manzolo-ollapdf-rag
echo "--- End OllaPDF Container Logs ---"
set -e

# Perform a health check
echo "Performing health check..."
curl -f http://localhost:8501

# Stop services
echo "Stopping services..."
docker compose -f docker-compose.yml -f docker-compose.cpu.yml down

echo "Removing docker network..."
docker network rm ollapdf-net || true
