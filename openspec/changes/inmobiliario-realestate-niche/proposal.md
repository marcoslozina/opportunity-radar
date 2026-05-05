# Proposal: Real Estate Niche Support en Opportunity Radar

## Intent

Extender Opportunity Radar para soportar investigación de mercado del dominio **inmobiliario argentino**, habilitando la detección semanal de oportunidades de contenido y producto en segmentos como: inversión inmobiliaria, créditos hipotecarios, mercado de alquileres y financiamiento en Argentina/Misiones.

Esto convierte a Opportunity Radar en el **motor de inteligencia de mercado** del proyecto `inmobiliario`, eliminando la necesidad de investigación manual y proveyendo señales de alta calidad para decidir qué contenido crear, qué features construir en la calculadora, y qué convierte mejor.

## Scope

### In Scope
- Nueva categoría predefinida: **"Inmobiliario Argentina"** disponible en el dashboard sin configuración extra.
- Set de keywords base para el dominio inmobiliario local (Misiones, Posadas, crédito hipotecario, etc.).
- Modo `real_estate` con scoring ajustado: prioriza `monetization_intent` y `frustration_level` sobre `trend_velocity` (el mercado inmobiliario tiene tendencias lentas pero alta intención de compra).
- Output del briefing adaptado: agrega columna "Aplicabilidad al proyecto inmobiliario" con etiquetas (`calculadora`, `contenido`, `feature`, `irrelevante`).

### Out of Scope
- Scraping de portales inmobiliarios (ZonaProp, ArgenProp) — requiere proxies y mantenimiento alto.
- Integración técnica directa entre los dos repositorios (quedan como proyectos independientes).
- Análisis de precios de propiedades específicas.

## Approach

1. Agregar `real_estate` como nuevo `discovery_mode` en la entidad `Niche`.
2. Crear `RealEstateScoringEngine` que rebalancee los pesos del scoring existente.
3. Pre-cargar keywords base del dominio en la capa de configuración (sin hardcodear en el dominio).
4. Agregar un `NicheTemplate` predefinido "Inmobiliario AR" que el usuario puede instanciar con un clic desde el dashboard.
5. Adaptar el briefing output para incluir el campo `real_estate_applicability`.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `src/domain/entities/niche.py` | Modified | Nuevo valor en `discovery_mode` enum |
| `src/application/services/scoring_engine.py` | Modified | Nueva subclase `RealEstateScoringEngine` |
| `src/application/use_cases/run_pipeline.py` | Modified | Routing al scoring engine correcto según `discovery_mode` |
| `src/domain/entities/briefing.py` | Modified | Campo opcional `real_estate_applicability` en `Opportunity` |
| `src/infrastructure/` | New | `niche_templates.py` con plantillas predefinidas |
| `dashboard.py` | Modified | Selector de template en la UI + columna nueva en tabla de resultados |
| `src/config.py` | Modified | `REAL_ESTATE_KEYWORDS_AR` como config externalizable |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Señales de HN/Reddit poco relevantes para inmobiliario local AR | Medium | Compensar con peso mayor en YouTube y Google Trends que son más locales |
| Baja frecuencia de señales (mercado lento) | Low | Ajustar scheduler a bisemanal en lugar de semanal para este nicho |

## Rollback Plan

El nuevo `discovery_mode` es aditivo — no modifica comportamiento existente. Revertir es eliminar la nueva subclase de scoring y el valor del enum. Cero riesgo para nichos existentes.

## Dependencies
- No hay dependencias externas nuevas.
- El proyecto `inmobiliario` consume los briefings manualmente (sin integración API por ahora).

## Success Criteria
- [ ] Crear nicho "Inversión Inmobiliaria Argentina" desde el dashboard y correr pipeline end-to-end sin errores.
- [ ] Briefing generado contiene al menos 5 oportunidades con `real_estate_applicability` correctamente etiquetado.
- [ ] `RealEstateScoringEngine` produce scores distintos (no idénticos) a `ScoringEngine` base para el mismo set de keywords.
- [ ] Tests unitarios del nuevo scoring engine pasan con 100% coverage de la lógica de pesos.
