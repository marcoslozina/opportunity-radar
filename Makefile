# Makefile — opportunity-radar
# Stack: Python / uv / FastAPI / Streamlit / Alembic

.PHONY: help dev dash migrate \
        run-pipeline run-content run-product \
        test test-unit test-int \
        lint format typecheck \
        clean

## ── Ayuda ────────────────────────────────────────────────────────────────────
help: ## Lista todos los comandos con descripción
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

## ── Desarrollo ───────────────────────────────────────────────────────────────
dev: ## Levantar uvicorn con --reload (PYTHONPATH=src)
	PYTHONPATH=src uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

dash: ## Levantar el dashboard de Streamlit
	uv run streamlit run dashboard.py

migrate: ## Aplicar migraciones de Alembic (alembic upgrade head)
	uv run alembic upgrade head

## ── Pipeline (requiere servidor corriendo en :8000) ──────────────────────────
run-pipeline: ## Correr content + product pipeline para un nicho (niche=<uuid>)
	@if [ -z "$(niche)" ]; then \
		echo "Error: pasá el niche id: make run-pipeline niche=<uuid>"; \
		exit 1; \
	fi
	curl -s -X POST http://localhost:8000/pipeline/run/$(niche) \
	  -H "Content-Type: application/json" \
	  -d '{"mode": "both"}' | python3 -m json.tool

run-content: ## Correr solo el content pipeline para un nicho (niche=<uuid>)
	@if [ -z "$(niche)" ]; then \
		echo "Error: pasá el niche id: make run-content niche=<uuid>"; \
		exit 1; \
	fi
	curl -s -X POST http://localhost:8000/pipeline/run/$(niche) \
	  -H "Content-Type: application/json" \
	  -d '{"mode": "content"}' | python3 -m json.tool

run-product: ## Correr solo el product pipeline para un nicho (niche=<uuid>)
	@if [ -z "$(niche)" ]; then \
		echo "Error: pasá el niche id: make run-product niche=<uuid>"; \
		exit 1; \
	fi
	curl -s -X POST http://localhost:8000/pipeline/run/$(niche) \
	  -H "Content-Type: application/json" \
	  -d '{"mode": "product"}' | python3 -m json.tool

## ── Tests ────────────────────────────────────────────────────────────────────
test: lint test-unit test-int ## Correr lint + tests unitarios + tests de integración

test-unit: ## Correr solo tests/unit/
	PYTHONPATH=src uv run pytest tests/unit/ -v

test-int: ## Correr solo tests/integration/
	PYTHONPATH=src uv run pytest tests/integration/ -v

## ── Calidad de código ────────────────────────────────────────────────────────
lint: ## Verificar estilo con ruff (ruff check src/)
	uv run ruff check src/

format: ## Formatear código con ruff (ruff format src/)
	uv run ruff format src/

typecheck: ## Verificar tipos con mypy (mypy src/)
	uv run mypy src/

## ── Limpieza ─────────────────────────────────────────────────────────────────
clean: ## Limpiar __pycache__, .pytest_cache, dist/, .mypy_cache
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "dist" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	@echo "Limpieza completa."
