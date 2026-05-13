FROM python:3.14-slim

RUN addgroup --system app && adduser --system --ingroup app app

WORKDIR /app

COPY pyproject.toml .
COPY src/ ./src/
COPY alembic/ ./alembic/
COPY alembic.ini .

RUN pip install --no-cache-dir uv && \
    uv pip install --system --no-cache -e .

USER app

EXPOSE 8000

ENV UVICORN_WORKERS=2

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD uvicorn src.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers ${UVICORN_WORKERS} \
    --no-access-log
