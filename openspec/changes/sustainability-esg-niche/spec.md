# Spec: ESG & Sustainability LATAM Niche en Opportunity Radar

## 1. Overview

Extensión **aditiva** del pipeline existente para el dominio ESG/Sustainability. Opportunity Radar actúa como **producto satélite** de `sustainability-rag-agent`: detecta señales de mercado sobre compliance ESG en LATAM y las convierte en oportunidades de features, contenido y posicionamiento para la plataforma principal.

No hay integración de código entre repositorios. El vínculo es operacional: el equipo lee los briefings de Opportunity Radar para informar la hoja de ruta de la plataforma ESG.

---

## 2. Nuevo Discovery Mode: `esg_intelligence`

### 2.1. Lógica de scoring — por qué estos pesos

El mercado ESG LATAM tiene características particulares:
- **Volumen de búsqueda bajo** pero creciente (el gap ES la oportunidad).
- **Alta frustración** con herramientas existentes (demasiado complejas, orientadas a Europa).
- **Alta intención de compra** cuando hay mandato regulatorio (NIS30 México 2026, CVM 193 Brasil).
- **Baja competencia de contenido** en español/portugués.

```python
# Engine base (actual)
WEIGHTS = {
    "social_signal": 0.25,
    "trend_velocity": 0.35,
    "competition_gap": 0.20,
    "monetization_intent": 0.10,
    "frustration_level": 0.10,
}

# ESGScoringEngine — ajustado para intelligence de plataforma B2B
ESG_WEIGHTS = {
    "social_signal": 0.10,
    "trend_velocity": 0.15,           # ↓ las regulaciones son lentas, no hay spikes
    "competition_gap": 0.30,          # ↑ gaps = features que nadie resuelve bien
    "monetization_intent": 0.20,      # mandato regulatorio = intención concreta
    "frustration_level": 0.25,        # ↑ dolor = ventaja competitiva a resolver
}
```

---

## 3. Keywords Base — `ESG_KEYWORDS_LATAM`

```python
ESG_KEYWORDS_LATAM = [
    # Compliance regulatorio
    "NIS30 Mexico empresas",
    "SFDR compliance latinoamerica",
    "CBAM carbon border adjustment Mexico",
    "CVM 193 Brasil ESG",
    "reporte de sostenibilidad obligatorio Argentina",

    # Dolor con herramientas actuales
    "calculadora huella de carbono empresa",
    "como medir scope 1 scope 2 scope 3",
    "software ESG pymes latinoamerica",
    "herramienta ESG en español",
    "reporte ESG sin consultora",

    # Oportunidades de contenido
    "que es ESG empresa mediana",
    "ISO 14064 explicado simple",
    "como hacer reporte de sostenibilidad",
    "ESG para manufactura Mexico",
    "inversores ESG latinoamerica",
]
```

---

## 4. NicheTemplate: "ESG LATAM"

Agregado al dict `TEMPLATES` en `infrastructure/niche_templates.py`:

```python
"esg_latam": NicheTemplate(
    name="ESG & Sustainability LATAM",
    keywords=ESG_KEYWORDS_LATAM,
    discovery_mode="esg_intelligence",
    description=(
        "Inteligencia de mercado ESG para LATAM. "
        "Detecta gaps de herramientas, oportunidades de contenido "
        "y señales de compliance regulatorio en México, Brasil y Argentina."
    ),
)
```

---

## 5. Campo de Briefing: `platform_implication`

Se generaliza el campo `real_estate_applicability` (del change anterior) a un campo polimórfico `domain_applicability: str = ""` en la entidad `Opportunity`. El valor específico depende del `discovery_mode`:

| `discovery_mode` | Valores posibles del campo |
|---|---|
| `real_estate` | `calculadora`, `contenido`, `feature`, `irrelevante` |
| `esg_intelligence` | `feature`, `contenido`, `posicionamiento`, `irrelevante` |
| `content` / `product` | campo vacío (no aplica) |

### Prompt de Claude para ESG mode

> "Para cada oportunidad, clasifica su implicación para una plataforma SaaS de ESG compliance para PYMEs LATAM usando exactamente uno de estos valores:
> - `feature` — hay un gap funcional que la plataforma puede resolver (ej: 'nadie explica cómo calcular Scope 3 categoría 11 de forma simple')
> - `contenido` — hay demanda de educación que se puede cubrir con blog/YouTube
> - `posicionamiento` — señal útil para afinar el ICP o el mensaje de ventas de la plataforma
> - `irrelevante` — no aplica al contexto de la plataforma"

---

## 6. Generalización de `Opportunity` (refactor menor)

Antes:
```python
@dataclass
class Opportunity:
    topic: str
    score: float
    recommended_action: str = ""
    real_estate_applicability: str = ""  # solo para real_estate mode
```

Después:
```python
@dataclass
class Opportunity:
    topic: str
    score: float
    recommended_action: str = ""
    domain_applicability: str = ""  # polimórfico: valor depende del discovery_mode del niche
```

**Nota:** Este refactor debe hacerse junto con el change `inmobiliario-realestate-niche` o antes. Si se hace después, requiere migración del campo en DB.

---

## 7. Cambios por Archivo

| Archivo | Tipo | Cambio |
|---|---|---|
| `src/domain/entities/niche.py` | Modified | Agrega `"esg_intelligence"` a discovery_mode |
| `src/domain/entities/opportunity.py` | Modified | Renombra `real_estate_applicability` → `domain_applicability` (coordinar con change inmobiliario) |
| `src/application/services/scoring_engine.py` | Modified | Nueva subclase `ESGScoringEngine` con `ESG_WEIGHTS` |
| `src/application/use_cases/run_pipeline.py` | Modified | Factory agrega caso `"esg_intelligence"` → `ESGScoringEngine` |
| `src/infrastructure/niche_templates.py` | Modified | Agrega template `esg_latam` |
| `src/config.py` | Modified | Agrega `ESG_KEYWORDS_LATAM: list[str]` |
| `dashboard.py` | Modified | Columna "Implicación" visible para `esg_intelligence` y `real_estate` modes |

---

## 8. Acceptance Criteria

- [ ] `Niche.create(discovery_mode="esg_intelligence")` no lanza excepción.
- [ ] `ESGScoringEngine.score(signals)` produce resultados distintos a `ScoringEngine.score(signals)` para el mismo input (verificar que los pesos impactan).
- [ ] Pipeline end-to-end con template "ESG LATAM" genera briefing con `domain_applicability` no vacío en al menos 3 oportunidades.
- [ ] Al migrar `real_estate_applicability` → `domain_applicability`, los tests del change inmobiliario siguen pasando.
- [ ] Tests: `test_esg_scoring_engine.py` con 3 casos: alta frustración, alto competition gap, todo neutral.
- [ ] Tests existentes NO rompen.

---

## 9. Orden de Implementación Recomendado

```
1. Change: inmobiliario-realestate-niche (crea niche_templates.py, campo domain_applicability)
2. Change: sustainability-esg-niche (este) — agrega ESGScoringEngine y template esg_latam
```

Si se implementan en paralelo, coordinar el rename del campo `Opportunity` para evitar conflicto de merge.

---

## 10. Out of Scope

- Scraping de regulaciones oficiales o diarios oficiales (DOF, BOE).
- Análisis competitivo directo de Persefoni, Watershed, etc.
- Integración API entre este repo y `sustainability-rag-agent`.
- Soporte multiidioma en el briefing output (todo en español).
