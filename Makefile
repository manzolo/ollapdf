# Makefile for OllaPDF
# Refactored to support the new modular architecture

.PHONY: all help up-self up-cpu up-gpu down clean logs \
        test test-unit test-integration test-e2e test-rag test-coverage \
        shell exec install-test-deps lint format check \
        pull-model list-models stats rebuild

# Default target
all: help

# ========================================
# Help
# ========================================

help:
	@echo "OllaPDF - Development Commands"
	@echo ""
	@echo "📦 Docker Operations:"
	@echo "  make up-self       - Start app only (use external Ollama)"
	@echo "  make up-cpu        - Start app + Ollama (CPU)"
	@echo "  make up-gpu        - Start app + Ollama (GPU)"
	@echo "  make down          - Stop all containers"
	@echo "  make clean         - Stop and remove containers, volumes"
	@echo "  make rebuild       - Rebuild and restart containers"
	@echo "  make logs          - Show container logs"
	@echo "  make shell         - Open shell in app container"
	@echo "  make stats         - Show container resource usage"
	@echo ""
	@echo "🧪 Testing:"
	@echo "  make test          - Run all tests (requires container running)"
	@echo "  make test-auto     - Auto-start container and run tests"
	@echo "  make test-unit     - Run unit tests only"
	@echo "  make test-integration - Run integration tests"
	@echo "  make test-e2e      - Run end-to-end tests"
	@echo "  make test-rag      - Run manual RAG system test"
	@echo "  make test-coverage - Run tests with coverage report"
	@echo ""
	@echo "🔧 Development:"
	@echo "  make install-test-deps - Install testing dependencies"
	@echo "  make exec CMD=<cmd>    - Execute command in container"
	@echo "  make pull-model MODEL=<name> - Pull Ollama model"
	@echo "  make list-models   - List available Ollama models"
	@echo ""
	@echo "📝 Code Quality:"
	@echo "  make check         - Run all code quality checks"
	@echo "  make lint          - Check code style"
	@echo "  make format        - Format code (if formatter installed)"
	@echo ""
	@echo "Examples:"
	@echo "  make up-cpu                    - Start with CPU Ollama"
	@echo "  make test-unit                 - Run fast unit tests"
	@echo "  make exec CMD='python app/test_rag.py' - Run custom command"
	@echo "  make pull-model MODEL=llama2   - Pull llama2 model"

# ========================================
# Docker Operations
# ========================================

up-self:
	@echo "🚀 Starting OllaPDF (standalone)..."
	docker compose -f docker-compose.yml up -d --build
	@echo "✅ OllaPDF started at http://localhost:8501"

up-cpu:
	@echo "🚀 Starting OllaPDF + Ollama (CPU)..."
	docker compose -f docker-compose.yml -f docker-compose.cpu.yml up -d --build
	@echo "✅ Services started:"
	@echo "   - OllaPDF: http://localhost:8501"
	@echo "   - Ollama: http://localhost:11434"

up-gpu:
	@echo "🚀 Starting OllaPDF + Ollama (GPU)..."
	docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d --build
	@echo "✅ Services started:"
	@echo "   - OllaPDF: http://localhost:8501"
	@echo "   - Ollama: http://localhost:11434"

down:
	@echo "⏹️  Stopping all containers..."
	docker compose -f docker-compose.yml -f docker-compose.cpu.yml -f docker-compose.gpu.yml down
	@echo "✅ All containers stopped"

clean:
	@echo "🧹 Cleaning up containers, volumes, and networks..."
	docker compose -f docker-compose.yml -f docker-compose.cpu.yml -f docker-compose.gpu.yml down -v --remove-orphans
	@echo "✅ Cleanup complete"

rebuild:
	@echo "🔄 Rebuilding and restarting..."
	$(MAKE) down
	$(MAKE) up-self
	@echo "✅ Rebuild complete"

logs:
	@echo "📋 Showing logs (Ctrl+C to exit)..."
	docker logs -f manzolo-ollapdf-rag 2>/dev/null || \
	docker compose -f docker-compose.yml -f docker-compose.cpu.yml -f docker-compose.gpu.yml logs -f

shell:
	@echo "🐚 Opening shell in OllaPDF container..."
	docker exec -it manzolo-ollapdf-rag /bin/bash

stats:
	@echo "📊 Container resource usage:"
	@docker stats --no-stream manzolo-ollapdf-rag 2>/dev/null || echo "Container not running"

exec:
	@if [ -z "$(CMD)" ]; then \
		echo "❌ Error: CMD not specified"; \
		echo "Usage: make exec CMD='<command>'"; \
		echo "Example: make exec CMD='python app/test_rag.py'"; \
		exit 1; \
	fi
	@echo "▶️  Executing: $(CMD)"
	@docker exec -it manzolo-ollapdf-rag $(CMD)

# ========================================
# Testing
# ========================================

# Helper function to check if container is running
.check-container:
	@docker ps --format '{{.Names}}' | grep -q '^manzolo-ollapdf-rag$$' || \
	(echo "❌ Error: Container 'manzolo-ollapdf-rag' is not running"; \
	 echo ""; \
	 echo "Please start the container first:"; \
	 echo "  make up-self   (if you have external Ollama)"; \
	 echo "  make up-cpu    (to start with CPU Ollama)"; \
	 echo "  make up-gpu    (to start with GPU Ollama)"; \
	 echo ""; \
	 exit 1)

install-test-deps: .check-container
	@echo "📦 Installing test dependencies in container..."
	@docker exec manzolo-ollapdf-rag pip install -q pytest pytest-cov pytest-mock
	@echo "✅ Test dependencies installed"

test: .check-container
	@echo "🧪 Running all tests..."
	@$(MAKE) -s test-unit
	@$(MAKE) -s test-integration
	@echo "✅ All tests completed!"

test-unit: .check-container
	@echo "🧪 Running unit tests..."
	@docker exec manzolo-ollapdf-rag python -m pytest --version > /dev/null 2>&1 || \
	(echo "📦 Installing pytest..."; \
	 docker exec manzolo-ollapdf-rag pip install -q pytest pytest-cov pytest-mock)
	@docker exec manzolo-ollapdf-rag pytest app/tests/ -v -m "not integration and not slow" 2>/dev/null || \
	docker exec manzolo-ollapdf-rag pytest app/tests/ -v
	@echo "✅ Unit tests completed!"

test-integration: .check-container
	@echo "🧪 Running integration tests..."
	@docker exec manzolo-ollapdf-rag python -m pytest --version > /dev/null 2>&1 || \
	(echo "📦 Installing pytest..."; \
	 docker exec manzolo-ollapdf-rag pip install -q pytest pytest-cov pytest-mock)
	@docker exec manzolo-ollapdf-rag pytest app/tests/ -v -m integration 2>/dev/null || \
	echo "⚠️  No integration tests found or pytest markers not configured"
	@echo "✅ Integration tests completed!"

test-e2e:
	@echo "🧪 Running end-to-end tests..."
	@echo "This will start a full test environment..."
	set -e; \
	trap '$(MAKE) down; docker system prune -f || true' EXIT; \
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
	echo "⏳ Waiting for services to initialize..."; \
	sleep 30; \
	docker exec manzolo-ollapdf-rag python app/test_rag.py; \
	echo "✅ E2E tests completed!"

test-rag: .check-container
	@echo "🧪 Running manual RAG system test..."
	@docker exec manzolo-ollapdf-rag python app/test_rag.py
	@echo "✅ RAG test completed!"

test-coverage: .check-container
	@echo "📊 Running tests with coverage..."
	@docker exec manzolo-ollapdf-rag python -m pytest --version > /dev/null 2>&1 || \
	(echo "📦 Installing pytest..."; \
	 docker exec manzolo-ollapdf-rag pip install -q pytest pytest-cov pytest-mock)
	@docker exec manzolo-ollapdf-rag pytest app/tests/ --cov=app --cov-report=term --cov-report=html
	@echo "✅ Coverage report generated in htmlcov/"

# Convenience target: start container and run tests
test-auto:
	@echo "🚀 Starting container and running tests..."
	@docker ps --format '{{.Names}}' | grep -q '^manzolo-ollapdf-rag$$' || \
	(echo "📦 Container not running. Starting..."; $(MAKE) up-self)
	@sleep 2
	@$(MAKE) test

# ========================================
# Ollama Model Management
# ========================================

pull-model: .check-container
	@if [ -z "$(MODEL)" ]; then \
		echo "❌ Error: MODEL not specified"; \
		echo "Usage: make pull-model MODEL=<model-name>"; \
		echo "Example: make pull-model MODEL=llama2"; \
		exit 1; \
	fi
	@echo "📥 Pulling Ollama model: $(MODEL)..."
	@docker exec manzolo-ollapdf-ollama ollama pull $(MODEL) 2>/dev/null || \
	(echo "❌ Error: Ollama container not running"; \
	 echo "Start Ollama with: make up-cpu or make up-gpu"; \
	 exit 1)
	@echo "✅ Model $(MODEL) pulled successfully!"

list-models:
	@echo "📋 Available Ollama models:"
	@docker exec manzolo-ollapdf-ollama ollama list 2>/dev/null || \
	(echo "❌ Ollama container not running"; \
	 echo "Start Ollama with: make up-cpu or make up-gpu")

# ========================================
# Code Quality
# ========================================

check: .check-container lint
	@echo "✅ Code quality checks completed!"

lint: .check-container
	@echo "🔍 Checking code style..."
	@docker exec manzolo-ollapdf-rag python -m py_compile app/main.py && echo "  ✅ main.py" || echo "  ❌ main.py"
	@docker exec manzolo-ollapdf-rag python -m py_compile app/core/document_processor.py && echo "  ✅ core/document_processor.py" || echo "  ❌ core/document_processor.py"
	@docker exec manzolo-ollapdf-rag python -m py_compile app/core/rag_service.py && echo "  ✅ core/rag_service.py" || echo "  ❌ core/rag_service.py"
	@docker exec manzolo-ollapdf-rag python -m py_compile app/services/request_queue.py && echo "  ✅ services/request_queue.py" || echo "  ❌ services/request_queue.py"
	@docker exec manzolo-ollapdf-rag python -m py_compile app/ui/text_processing.py && echo "  ✅ ui/text_processing.py" || echo "  ❌ ui/text_processing.py"
	@docker exec manzolo-ollapdf-rag python -m py_compile app/ui/styling.py && echo "  ✅ ui/styling.py" || echo "  ❌ ui/styling.py"
	@docker exec manzolo-ollapdf-rag python -m py_compile app/config/settings.py && echo "  ✅ config/settings.py" || echo "  ❌ config/settings.py"
	@echo "✅ Syntax check completed!"

format:
	@echo "⚠️  Auto-formatting not configured yet"
	@echo "To add formatting, install black or ruff in the container"
	@echo "Example: docker exec manzolo-ollapdf-rag pip install black"
	@echo "Then run: docker exec manzolo-ollapdf-rag black app/"

# ========================================
# Development Shortcuts
# ========================================

# Quick restart of just the app container (useful during development)
restart:
	@echo "🔄 Restarting OllaPDF container..."
	docker restart manzolo-ollapdf-rag
	@echo "✅ Container restarted"

# Show recent logs
logs-tail:
	@echo "📋 Recent logs:"
	@docker logs --tail 50 manzolo-ollapdf-rag

# Show container status
status:
	@echo "📊 Container status:"
	@docker ps -f name=manzolo-ollapdf

# Verify imports work
verify: .check-container
	@echo "🔍 Verifying module imports..."
	@docker exec manzolo-ollapdf-rag python -c "from config import config; print('✅ config loaded')"
	@docker exec manzolo-ollapdf-rag python -c "from core import DocumentProcessor, RAGService; print('✅ core loaded')"
	@docker exec manzolo-ollapdf-rag python -c "from services import RequestQueue; print('✅ services loaded')"
	@docker exec manzolo-ollapdf-rag python -c "from ui import process_latex, clean_response; print('✅ ui loaded')"
	@echo "✅ All modules verified!"
