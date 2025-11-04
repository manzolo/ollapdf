# Makefile for Docker Compose

.PHONY: all help up-self up-cpu up-gpu down clean logs

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

up-self:
	docker compose -f docker-compose.yml up -d --build

up-cpu:
	docker compose -f docker-compose.yml -f docker-compose.cpu.yml up -d --build

up-gpu:
	docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d --build

down:
	docker compose -f docker-compose.yml -f docker-compose.cpu.yml -f docker-compose.gpu.yml down

clean:
	docker compose -f docker-compose.yml -f docker-compose.cpu.yml -f docker-compose.gpu.yml down -v --remove-orphans

logs:
	docker logs ollapdf-app-self || true
	docker compose -f docker-compose.yml -f docker-compose.cpu.yml -f docker-compose.gpu.yml logs -f || true
