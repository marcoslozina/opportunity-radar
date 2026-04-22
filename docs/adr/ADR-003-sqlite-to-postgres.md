# ADR-003: SQLite en dev, Postgres en producción

**Estado:** Aceptado
**Fecha:** 2026-04-22

## Contexto

Necesitamos persistencia async. En desarrollo queremos arrancar sin Docker ni servicios externos.

## Decisión

`DATABASE_URL` configura el motor vía env var:
- Dev default: `sqlite+aiosqlite:///./opportunity_radar.db`
- Prod: `postgresql+asyncpg://...`

SQLAlchemy 2.0 async abstrae la diferencia. Alembic maneja las migraciones en ambos entornos.

## Consecuencias

### Positivas
- Dev sin Docker, setup en segundos
- Mismo código y migraciones para ambos entornos

### Negativas / Tradeoffs
- SQLite no soporta todas las features de Postgres (ej. `RETURNING` en bulk inserts)
- Tests de integración deben usar SQLite in-memory, no Postgres real
