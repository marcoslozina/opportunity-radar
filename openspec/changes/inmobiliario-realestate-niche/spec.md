# Spec: Real Estate Niche Support en Opportunity Radar

## 1. Overview

Extensión del pipeline existente para soportar el dominio inmobiliario argentino. El cambio es **aditivo y no rompe nada** — se agrega un nuevo `discovery_mode` llamado `real_estate` con su propio scoring engine y un template predefinido en el dashboard.

---

## 2. Nuevo Discovery Mode: `real_estate`

### 2.1. Diferencias vs. modo `content` / `product`

| Dimensión | content / product | real_estate |
|---|---|---|
| Frecuencia de tendencias | Alta (weekly spikes) | Baja (mercado lento, tendencias de meses) |
| Señal más valiosa | `trend_velocity` | `monetization_intent` + `frustration_level` |
| Fuente más relevante | Reddit, HackerNews | YouTube, Google Trends, SerpAPI |
| Ciclo de análisis | Semanal | Bisemanal |

### 2.2. RealEstateScoringEngine — Pesos

```python
# Scoring engine base (actual)
WEIGHTS = {
    "social_signal": 0.25,
    "trend_velocity": 0.35,
    "competition_gap": 0.20,
    "monetization_intent": 0.10,
    "frustration_level": 0.10,
}

# Nuevo RealEstateScoringEngine
REAL_ESTATE_WEIGHTS = {
    "social_signal": 0.15,
    "trend_velocity": 0.15,        # ↓ menos importante
    "competition_gap": 0.20,
    "monetization_intent": 0.30,   # ↑ alguien buscando crédito = intención real
    "frustration_level": 0.20,     # ↑ "no puedo pagar alquiler" = dolor real
}
```

---

## 3. Keywords Base del Dominio

Cargadas desde `config.py` como `REAL_ESTATE_KEYWORDS_AR`. El usuario puede editarlas o agregar más desde el dashboard.

```python
REAL_ESTATE_KEYWORDS_AR = [
    "crédito hipotecario Argentina",
    "invertir en propiedades Argentina",
    "comprar departamento Misiones",
    "alquiler vs compra Argentina",
    "UVA hipotecario 2025",
    "propiedades en Posadas Misiones",
    "calculadora crédito hipotecario",
    "ROI inmobiliario Argentina",
    "Banco Nación hipotecario",
    "cómo invertir en inmuebles con poco capital",
]
```

---

## 4. NicheTemplate: "Inmobiliario AR"

Nuevo concepto `NicheTemplate` en `infrastructure/niche_templates.py`:

```python
@dataclass(frozen=True)
class NicheTemplate:
    name: str
    keywords: list[str]
    discovery_mode: str
    description: str

TEMPLATES = {
    "real_estate_ar": NicheTemplate(
        name="Inmobiliario Argentina",
        keywords=REAL_ESTATE_KEYWORDS_AR,
        discovery_mode="real_estate",
        description="Oportunidades de contenido y producto en el mercado inmobiliario argentino.",
    )
}
```

---

## 5. Cambios en el Briefing Output

### 5.1. Nuevo campo en `Opportunity`

```python
@dataclass
class Opportunity:
    topic: str
    score: float
    recommended_action: str = ""
    real_estate_applicability: str = ""  # NUEVO: "calculadora" | "contenido" | "feature" | "irrelevante"
```

### 5.2. Prompt para el InsightPort (Claude)

Cuando `discovery_mode == "real_estate"`, el insight prompt incluye:

> "Para cada oportunidad, además de la acción recomendada, clasifica su aplicabilidad al proyecto 'sistema-leads-inmobiliario' usando exactamente uno de estos valores: `calculadora` (mejora para la calculadora financiera), `contenido` (tema para canal YouTube/blog), `feature` (nueva funcionalidad del bot WhatsApp), `irrelevante`."

---

## 6. Cambios en el Dashboard

- **Panel "Crear Nicho"**: Agregar selector de template. Al elegir "Inmobiliario AR", pre-rellena nombre y keywords automáticamente.
- **Tabla de Briefing**: Columna adicional "Aplicabilidad" visible solo cuando `discovery_mode == "real_estate"`.
- **Scheduler**: Para nichos `real_estate`, el cron se ajusta a `0 8 * * 1,4` (lunes y jueves) en lugar de solo lunes.

---

## 7. Cambios por Archivo

| Archivo | Tipo | Cambio |
|---|---|---|
| `src/domain/entities/niche.py` | Modified | `discovery_mode` acepta `"real_estate"` |
| `src/domain/entities/opportunity.py` | Modified | Campo `real_estate_applicability: str = ""` |
| `src/application/services/scoring_engine.py` | Modified | Subclase `RealEstateScoringEngine` con pesos propios |
| `src/application/use_cases/run_pipeline.py` | Modified | Factory: selecciona scoring engine según `discovery_mode` |
| `src/infrastructure/niche_templates.py` | New | Dataclass `NicheTemplate` + dict `TEMPLATES` |
| `src/config.py` | Modified | `REAL_ESTATE_KEYWORDS_AR: list[str]` |
| `dashboard.py` | Modified | Selector de template + columna "Aplicabilidad" |

---

## 8. Acceptance Criteria

- [ ] `Niche.create(name="X", keywords=[], discovery_mode="real_estate")` no lanza excepción.
- [ ] `RealEstateScoringEngine.score(signals)` produce pesos distintos a `ScoringEngine.score(signals)` para el mismo input.
- [ ] Pipeline end-to-end con nicho `real_estate` genera briefing con campo `real_estate_applicability` no vacío.
- [ ] Template "Inmobiliario AR" pre-rellena el form del dashboard correctamente.
- [ ] Tests unitarios: `test_real_estate_scoring_engine.py` con al menos 3 casos (alta monetización, alta frustración, todo en cero).
- [ ] Tests existentes NO rompen (cambio aditivo, backwards compatible).

---

## 9. Out of Scope

- Scraping de ArgenProp / ZonaProp.
- Integración API directa con el proyecto `inmobiliario`.
- Soporte multi-idioma en el briefing (todo en español para este dominio).
