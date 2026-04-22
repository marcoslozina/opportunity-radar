# ADR-004: Claude API para síntesis de insights

**Estado:** Aceptado
**Fecha:** 2026-04-22

## Contexto

El scoring engine calcula dimensiones numéricas, pero la acción recomendada necesita lenguaje natural contextualizado al nicho del usuario.

## Decisión

Usar `claude-sonnet-4-6` con prompt caching para generar las `recommended_action` de cada oportunidad. El system prompt se cachea (TTL 5 min) para reducir costos hasta un 90% en llamadas repetidas.

## Consecuencias

### Positivas
- Acciones en lenguaje natural, contextualizadas y accionables
- Prompt caching reduce costo significativamente en pipelines recurrentes
- Fácil ajustar el tono/formato del output cambiando el system prompt

### Negativas / Tradeoffs
- Costo por token escala con cantidad de nichos y keywords
- Dependencia de disponibilidad de la API de Anthropic

## Alternativas descartadas
- **Reglas fijas por score**: descartado porque produce acciones genéricas sin valor real
- **Modelo local**: descartado por complejidad de setup y menor calidad de output
