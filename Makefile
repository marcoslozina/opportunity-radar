# Makefile — comandos unificados del proyecto
# Adaptar según el stack elegido en el setup de sesión

.PHONY: help dev test test-unit test-integration lint format typecheck build clean

## ── Ayuda ────────────────────────────────────────────
help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

## ── Desarrollo ───────────────────────────────────────
dev: ## Levantar el servidor de desarrollo
	@echo "Adaptar según el stack: uvicorn / npm run dev / gradle bootRun"

## ── Tests ────────────────────────────────────────────
test: lint test-unit test-integration ## Correr todos los checks (lint + tests)

test-unit: ## Correr solo tests unitarios
	@echo "Python: pytest tests/unit/"
	@echo "Java:   ./gradlew test"
	@echo "Node:   npm run test:unit"

test-integration: ## Correr tests de integración (requiere Docker)
	@echo "Python: pytest tests/integration/"
	@echo "Java:   ./gradlew integrationTest"
	@echo "Node:   npm run test:integration"

## ── Calidad de código ────────────────────────────────
lint: ## Correr linter
	@echo "Python: ruff check src/"
	@echo "Java:   ./gradlew checkstyleMain"
	@echo "Node:   npm run lint"

format: ## Formatear código
	@echo "Python: ruff format src/"
	@echo "Node:   npm run format"

typecheck: ## Verificar tipos
	@echo "Python: mypy src/"
	@echo "Node:   tsc --noEmit"

## ── Build ────────────────────────────────────────────
build: ## Build del proyecto
	@echo "Python: uv build"
	@echo "Java:   ./gradlew build"
	@echo "Node:   npm run build"

## ── Limpieza ─────────────────────────────────────────
clean: ## Limpiar artefactos de build
	@echo "Python: rm -rf dist/ build/ __pycache__/"
	@echo "Java:   ./gradlew clean"
	@echo "Node:   rm -rf dist/ node_modules/.cache"
