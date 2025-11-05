# Makefile for Docker Compose

.PHONY: all help up-self up-cpu up-gpu down clean logs test

all: help

help:
	@echo "Usage:"
	@echo "  make up-self   - Start the app container only, connecting to an external Ollama instance on the host."
	@echo "                   (Uses docker-compose.yml)"
	@echo "  make up-cpu    - Start app and Ollama (CPU) containers. (Uses docker-compose.yml and docker-compose.cpu.yml)"
	@echo "  make up-gpu    - Start app and Ollama (GPU) containers. (Uses docker-compose.yml and docker-compose.gpu.yml)"
	@echo "  make down      - Stop and remove all containers from all configurations."
	@echo "  make clean     - Stop, remove containers, and remove volumes/networks from all configurations."
	@echo "  make logs      - Display logs for all running containers (docker compose and 'self' app)."
	@echo "  make test      - Run the RAG system tests."

up-self:
	docker compose -f docker-compose.yml up -d --build

up-cpu:
	docker compose -f docker-compose.yml -f docker-compose.cpu.yml up -d --build

up-gpu:
	docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d --build

test:
	@echo "Running RAG system tests..."
	set -e; \
	trap 'make down; docker system prune -f || true' EXIT; \
	export OLLAMA_MODEL_NAME=phi; \
	docker compose -f docker-compose.yml -f docker-compose.cpu.yml build; \
	docker pull ollama/ollama; \
	docker run -d -p 11434:11434 --name temp-ollama -v $(shell pwd)/ollama_data:/root/.ollama ollama/ollama; \
	./wait-for-it.sh localhost:11434 --timeout=120; \
	docker exec temp-ollama ollama pull phi; \
	docker stop temp-ollama; \
	docker rm temp-ollama; \
	docker compose -f docker-compose.yml -f docker-compose.cpu.yml up -d; \
	./wait-for-it.sh localhost:11434 --timeout=120; \
	./wait-for-it.sh localhost:8501 --timeout=60; \
	echo "Giving Streamlit app more time to initialize..."; \
	sleep 30; \
	docker compose exec ollapdf python test_rag.py;

down:
	docker compose -f docker-compose.yml -f docker-compose.cpu.yml -f docker-compose.gpu.yml down

clean:
	docker compose -f docker-compose.yml -f docker-compose.cpu.yml -f docker-compose.gpu.yml down -v --remove-orphans

logs:
	docker logs ollapdf-app-self || true
	docker compose -f docker-compose.yml -f docker-compose.cpu.yml -f docker-compose.gpu.yml logs -f || true
