# Core Specification: Opportunity Radar

## Purpose

Define el comportamiento del sistema de scoring de oportunidades: gestión de nichos, recolección de señales, scoring y generación de briefings semanales.

---

## Requirements

### Requirement: Niche Management

El sistema MUST permitir crear, listar y eliminar nichos. Un nicho MUST tener un nombre y al menos una keyword base.

#### Scenario: Crear un nicho válido

- GIVEN el sistema no tiene ningún nicho con el nombre "Angular"
- WHEN se envía POST /niches con `{ "name": "Angular", "keywords": ["angular signals", "angular 17"] }`
- THEN el sistema retorna 201 con el nicho creado e `id` generado
- AND el nicho queda persistido

#### Scenario: Keyword base vacía

- GIVEN un request de creación de nicho
- WHEN se envía con `keywords: []`
- THEN el sistema retorna 422 con error `KEYWORDS_REQUIRED`

---

### Requirement: Signal Collection

El sistema MUST recolectar señales de todas las fuentes configuradas para cada keyword de un nicho. Si una fuente falla, MUST continuar con las demás y registrar el error.

#### Scenario: Recolección exitosa multi-fuente

- GIVEN un nicho con keyword "angular signals"
- WHEN se dispara el pipeline de recolección
- THEN el sistema retorna señales de ≥ 4 fuentes distintas
- AND cada señal contiene `source`, `topic`, `raw_value`, `collected_at`

#### Scenario: Falla de una fuente

- GIVEN una fuente (ej. SerpAPI) retorna timeout
- WHEN se ejecuta la recolección
- THEN el sistema completa con las fuentes restantes
- AND registra un log de error con `source` y `reason`
- AND NO falla el pipeline completo

---

### Requirement: Opportunity Scoring

El sistema MUST calcular un `OpportunityScore` (0–100) por topic con 4 dimensiones: `trend_velocity`, `competition_gap`, `social_signal`, `monetization_intent`. Cada dimensión MUST estar normalizada a 0–10.

#### Scenario: Score calculado correctamente

- GIVEN señales recolectadas para "angular signals" de ≥ 3 fuentes
- WHEN se ejecuta el scoring engine
- THEN el sistema retorna un `OpportunityScore` con las 4 dimensiones y un score total
- AND `score_total` == weighted_average(dimensiones) normalizado a 0–100

#### Scenario: Datos insuficientes

- GIVEN un topic con señales de solo 1 fuente
- WHEN se calcula el score
- THEN el sistema SHOULD calcular el score con las dimensiones disponibles
- AND marca `confidence: "low"` en el resultado

---

### Requirement: Briefing Generation

El sistema MUST generar un briefing semanal por nicho con los top 10 topics por score. Cada entrada MUST incluir score total, dimensiones, y una acción recomendada generada por Claude API.

#### Scenario: Briefing generado exitosamente

- GIVEN un nicho con ≥ 10 oportunidades scored
- WHEN se solicita GET /briefing/{niche_id}
- THEN el sistema retorna un briefing con exactamente 10 oportunidades
- AND ordenadas por `score_total` descendente
- AND cada una contiene `recommended_action` (string no vacío)

#### Scenario: Menos de 10 oportunidades disponibles

- GIVEN un nicho con 6 oportunidades scored
- WHEN se solicita el briefing
- THEN el sistema retorna las 6 disponibles
- AND NO retorna error

---

### Requirement: Pipeline Scheduler

El sistema MUST ejecutar el pipeline (collect → score → briefing) de forma automática una vez por semana por cada nicho activo. El schedule MUST ser configurable vía variable de entorno.

#### Scenario: Ejecución automática semanal

- GIVEN el scheduler está activo y hay 1 nicho configurado
- WHEN transcurre el intervalo configurado (default: lunes 08:00 UTC)
- THEN el sistema ejecuta collect → score → briefing para ese nicho
- AND persiste el briefing generado

#### Scenario: Pipeline ya en ejecución

- GIVEN el pipeline está corriendo para un nicho
- WHEN el scheduler intenta disparar otro pipeline para el mismo nicho
- THEN el sistema MUST ignorar el segundo trigger
- AND loggea `PIPELINE_ALREADY_RUNNING` para ese nicho

---

### Requirement: API Observability

El sistema MUST exponer `/health` y `/docs`. Cada request MUST loggear `request_id`, `method`, `path`, `status`, `duration_ms`.

#### Scenario: Health check

- GIVEN el sistema está corriendo
- WHEN se hace GET /health
- THEN retorna 200 con `{ "status": "ok", "scheduler": "running" | "stopped" }`
