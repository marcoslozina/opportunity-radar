# ADR-003: Product Discovery como dominio separado

**Estado:** Aceptado
**Fecha:** 2026-04-22

## Contexto

El sistema necesita evaluar nichos desde una perspectiva de monetización de productos (ebooks, micro-SaaS, servicios). Esto requiere nuevas entidades, señales y clasificación por IA que no existen en el dominio de content scoring actual.

## Decisión 1 — Dominio separado para Product Discovery

Crear entidades propias (`ProductOpportunity`, `ProductBriefing`, `ProfitabilityScore`, `ProductType`) en un dominio independiente, en lugar de extender `Opportunity` con campos opcionales.

## Consecuencias de Decisión 1

### Positivas
- Cada dominio evoluciona de forma independiente sin riesgo de regresión en el otro
- No hay nullables condicionales: `product_type`, `price_range` no tienen sentido en content scoring
- Separación de concerns clara: content scoring vs product monetization

### Negativas / Tradeoffs
- Más archivos y entidades para mantener
- No hay reutilización directa de `Opportunity`; datos similares viven en estructuras paralelas

## Alternativas descartadas (Decisión 1)
- **Extender `Opportunity` con nullable columns**: descartado porque genera code smell de campos condicionales (`if product_type is not None`) que contaminan el modelo de dominio

---

## Decisión 2 — FrustrationSignalAdapter implementa TrendDataPort

`FrustrationSignalAdapter` implementa el puerto existente `TrendDataPort` (contrato `collect(keywords)`) en lugar de definir un puerto nuevo `FrustrationPort`.

## Consecuencias de Decisión 2

### Positivas
- `RunProductDiscoveryUseCase` reutiliza el pipeline de recolección sin cambios en la interfaz
- El tipo de señal se diferencia por `signal_type="frustration_level"`, no por la interfaz
- Un adapter nuevo no requiere modificar el use case

### Negativas / Tradeoffs
- `TrendDataPort` es un contrato más genérico que el propósito específico de frustration signals; puede resultar demasiado amplio si la semántica diverge en el futuro

## Alternativas descartadas (Decisión 2)
- **Puerto nuevo `FrustrationPort`**: descartado porque duplica el contrato de recolección sin aportar diferenciación funcional; hubiera requerido cambios en el use case para cada nuevo tipo de señal

---

## Decisión 3 — ProductType clasificado por Claude

`ClaudeProductDiscoveryAdapter` clasifica el `ProductType` (EBOOK, MICRO_SAAS, SERVICE, DIGITAL_PRODUCT) mediante llamada a la API de Claude, con fallback a `DIGITAL_PRODUCT` si la confianza es baja.

## Consecuencias de Decisión 3

### Positivas
- Clasificación contextual basada en lenguaje natural: entiende matices que reglas hardcodeadas no cubren
- Flexible ante casos nuevos sin modificar código
- Incluye `reasoning` y `recommended_price_range` en la misma respuesta

### Negativas / Tradeoffs
- Latencia y costo por llamada a la API de Claude
- No determinista: dos ejecuciones con el mismo input pueden producir tipos distintos

## Alternativas descartadas (Decisión 3)
- **Reglas determinísticas** (`if competition_gap > 7 → MICRO_SAAS`): descartado porque los umbrales son arbitrarios y frágiles; no captura contexto semántico del nicho

---

## Decisión 4 — `discovery_mode` como campo string en Niche

Agregar `discovery_mode: str = "content"` directamente en el dataclass `Niche`, en lugar de una tabla pivot separada.

## Consecuencias de Decisión 4

### Positivas
- Cambio aditivo: no rompe ningún código existente ni migración destructiva
- Los valores posibles son un enum estable y acotado: `"content"`, `"product"`, `"both"`
- Lógica del scheduler trivial: `if niche.discovery_mode in ("product", "both")`

### Negativas / Tradeoffs
- Validación del enum delegada a la capa de API (Pydantic) en vez de estar garantizada por el modelo de base de datos

## Alternativas descartadas (Decisión 4)
- **Tabla pivot `niche_discovery_modes`**: descartado por over-engineering para un campo con tres valores posibles y semántica fija
