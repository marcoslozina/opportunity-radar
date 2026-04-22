# Product Discovery Specification

## Purpose

Define el comportamiento del módulo de descubrimiento de productos: detección de pain points, scoring de rentabilidad, clasificación de tipo de producto y generación de briefings orientados a monetización.

---

## Requirements

### Requirement: Niche Discovery Mode

El sistema MUST permitir configurar `discovery_mode` en un nicho al crearlo o actualizarlo. Los valores válidos son `"content"`, `"product"` y `"both"`. El default MUST ser `"content"` para no romper el comportamiento existente.

#### Scenario: Crear nicho en modo product

- GIVEN no existe un nicho llamado "Angular"
- WHEN se envía POST /niches con `{ "name": "Angular", "keywords": [...], "discovery_mode": "product" }`
- THEN el sistema retorna 201 con `discovery_mode: "product"`
- AND el scheduler registra un job de product discovery para ese nicho

#### Scenario: Modo inválido

- GIVEN un request de creación de nicho
- WHEN se envía con `discovery_mode: "unknown"`
- THEN el sistema retorna 422 con error `INVALID_DISCOVERY_MODE`

---

### Requirement: Frustration Signal Collection

El sistema MUST recolectar señales de frustración de Reddit y HN usando query patterns orientados a pain points. Si una fuente falla, MUST continuar con las demás.

#### Scenario: Señales de frustración detectadas

- GIVEN un nicho con keyword "project management"
- WHEN se ejecuta la recolección de frustración
- THEN el sistema retorna señales con `signal_type: "frustration_level"`
- AND cada señal contiene `source`, `topic`, `raw_value` (0–1), `collected_at`

#### Scenario: Sin resultados de frustración

- GIVEN una keyword muy específica sin posts de dolor
- WHEN se ejecuta la recolección
- THEN el sistema retorna lista vacía para esa keyword
- AND el pipeline continúa sin error

---

### Requirement: Profitability Scoring

El sistema MUST calcular un `ProfitabilityScore` (0–100) por topic con 4 dimensiones: `frustration_level`, `market_size`, `competition_gap`, `willingness_to_pay`. Cada dimensión MUST estar normalizada a 0–10.

#### Scenario: Score calculado con señales suficientes

- GIVEN señales de frustración + competencia + monetización para "project management"
- WHEN se ejecuta el scoring de rentabilidad
- THEN el sistema retorna un `ProfitabilityScore` con las 4 dimensiones y `total` (0–100)
- AND `confidence` refleja la cantidad de fuentes disponibles

#### Scenario: Score con señales mínimas

- GIVEN solo señales de 1 fuente para un topic
- WHEN se calcula el profitability score
- THEN el sistema calcula con las dimensiones disponibles
- AND marca `confidence: "low"`

---

### Requirement: Product Classification

El sistema MUST asignar un `ProductType` a cada `ProductOpportunity`. Los valores válidos son `ebook`, `micro-saas`, `service`, `digital-product`. La clasificación MUST ser realizada por Claude usando el contexto completo de señales.

#### Scenario: Clasificación exitosa

- GIVEN un topic con ProfitabilityScore calculado y señales disponibles
- WHEN se ejecuta la clasificación
- THEN cada `ProductOpportunity` tiene `product_type` asignado (no vacío)
- AND tiene `product_reasoning` explicando el por qué (no vacío)
- AND tiene `recommended_price_range` (ej: "$29–$49")

#### Scenario: Fallback cuando Claude no puede clasificar

- GIVEN un topic con señales insuficientes para clasificar
- WHEN Claude no puede determinar el tipo con confianza
- THEN el sistema asigna `product_type: "digital-product"` como fallback
- AND `product_reasoning` indica que la clasificación es tentativa

---

### Requirement: Product Briefing

El sistema MUST generar un `ProductBriefing` por nicho con el top 5 de `ProductOpportunity` ordenado por `profitability_score` descendente.

#### Scenario: Briefing generado exitosamente

- GIVEN un nicho con ≥ 5 product opportunities scored
- WHEN se solicita GET /product-briefing/{niche_id}
- THEN retorna las 5 oportunidades con mayor `profitability_score`
- AND cada una tiene `product_type`, `product_reasoning`, `recommended_price_range`

#### Scenario: Menos de 5 oportunidades disponibles

- GIVEN un nicho con 3 product opportunities
- WHEN se solicita el product briefing
- THEN retorna las 3 disponibles sin error

#### Scenario: Nicho sin product briefing

- GIVEN un nicho con `discovery_mode: "content"` (sin product discovery)
- WHEN se solicita GET /product-briefing/{niche_id}
- THEN retorna 404 con mensaje claro

---

### Requirement: Pipeline Isolation

El product discovery pipeline MUST correr de forma independiente al content pipeline. Una falla en el product pipeline NO MUST afectar el content pipeline y viceversa.

#### Scenario: Falla en product pipeline no afecta content

- GIVEN un nicho con `discovery_mode: "both"`
- WHEN el product discovery pipeline lanza una excepción
- THEN el content pipeline completa normalmente
- AND el error del product pipeline queda loggeado
