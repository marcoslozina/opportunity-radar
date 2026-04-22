# ADR-002: APScheduler embebido en FastAPI

**Estado:** Aceptado
**Fecha:** 2026-04-22

## Contexto

El pipeline semanal necesita correr automáticamente por cada nicho activo. La alternativa natural es una cola de tareas con workers separados.

## Decisión

Usar APScheduler (`AsyncIOScheduler`) embebido en el lifespan de FastAPI, con `coalesce=True` y `max_instances=1` por job para evitar ejecuciones duplicadas.

## Consecuencias

### Positivas
- Sin infra adicional (no Redis, no workers separados)
- Deploy simple: un solo proceso
- Migrable a Celery cuando la carga lo justifique

### Negativas / Tradeoffs
- Si el proceso cae, los jobs pendientes no se recuperan automáticamente
- No escala horizontalmente (múltiples instancias dispararían el job N veces)

## Alternativas descartadas
- **Celery + Redis**: descartado por complejidad de infra innecesaria para el MVP
- **Cron del sistema operativo**: descartado porque requiere acceso al host y no es portable
