# Proposal: ESG/Sustainability Niche Support en Opportunity Radar

## Intent

Convertir Opportunity Radar en el **motor de inteligencia de mercado** del proyecto `sustainability-rag-agent`, habilitando la detección semanal de:
- Qué están preguntando las empresas sobre ESG/compliance en LATAM (→ features para la plataforma)
- Qué contenido sobre ESG tiene mayor oportunidad de ranking (→ estrategia de content marketing)
- Qué frustraciones tienen los usuarios de herramientas ESG existentes (→ ventajas competitivas para posicionar)

La relación es de **producto satélite**: Opportunity Radar alimenta la hoja de ruta de Sustainability Intelligence Platform con señales de mercado reales, sin integración de código entre repos.

## Scope

### In Scope
- Nueva categoría predefinida: **"ESG & Sustainability LATAM"** en el dashboard.
- Set de keywords base multi-región: México (NIS30), Brasil (CVM 193), Argentina, España (SFDR/CBAM).
- Modo `esg_intelligence` con scoring ajustado: prioriza `frustration_level` (qué no resuelven las herramientas actuales) y `competition_gap` (qué nadie está respondiendo bien aún).
- Briefing con columna `platform_implication`: etiqueta cómo aplicar la oportunidad a Sustainability Intelligence Platform (`feature`, `contenido`, `posicionamiento`, `irrelevante`).
- Template predefinido "ESG LATAM" instanciable con 1 clic.

### Out of Scope
- Integración API con sustainability-rag-agent (son repos independientes).
- Scraping de regulaciones oficiales (BOE, DOF, etc.) — requiere parsers específicos por país.
- Análisis de competidores ESG directos (Persefoni, Watershed, etc.) en V1.

## Approach

1. Agregar `esg_intelligence` como nuevo `discovery_mode` en la entidad `Niche`.
2. Crear `ESGScoringEngine` que rebalancee pesos del engine base: máximo peso en `frustration_level` y `competition_gap` (las señales más valiosas para identificar gaps que una plataforma ESG puede resolver).
3. Pre-cargar keywords ESG LATAM en `config.py` externalizable.
4. Agregar template "ESG LATAM" al módulo `niche_templates.py` (que también tendrá el template inmobiliario).
5. Adaptar briefing con campo `platform_implication` vía prompt especializado para Claude.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `src/domain/entities/niche.py` | Modified | Nuevo valor `esg_intelligence` en `discovery_mode` |
| `src/application/services/scoring_engine.py` | Modified | Nueva subclase `ESGScoringEngine` |
| `src/application/use_cases/run_pipeline.py` | Modified | Routing al engine correcto según `discovery_mode` |
| `src/domain/entities/opportunity.py` | Modified | Campo `platform_implication: str = ""` (comparte campo con `real_estate_applicability` o se generaliza a `domain_applicability`) |
| `src/infrastructure/niche_templates.py` | Modified | Agregar template `esg_latam` al dict `TEMPLATES` |
| `src/config.py` | Modified | `ESG_KEYWORDS_LATAM: list[str]` |
| `dashboard.py` | Modified | Template selector + columna "Implicación" en la tabla de briefing |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Keywords en inglés dominan los resultados (Reddit/HN son en inglés) | High | Incluir keywords en español + portugués; dar más peso a YouTube que tiene contenido LATAM |
| El mercado ESG LATAM tiene poco volumen de búsqueda orgánica aún | Medium | El gap es precisamente la oportunidad: poca competencia de contenido = más fácil rankear |

## Rollback Plan
Cambio aditivo. Eliminar la subclase `ESGScoringEngine` y el valor del enum. Cero impacto en nichos existentes.

## Dependencies
- `niche_templates.py` (creado en el change `inmobiliario-realestate-niche`) debe existir primero.
- No hay dependencias externas nuevas.

## Success Criteria
- [ ] Crear nicho "ESG LATAM" desde el dashboard con template y correr pipeline end-to-end.
- [ ] Briefing contiene al menos 5 oportunidades con `platform_implication` no vacío.
- [ ] `ESGScoringEngine` produce resultados distintos al engine base (pesos verificados en tests).
- [ ] Al menos 1 oportunidad etiquetada como `feature` mapea a una mejora identificada en `sustainability-intelligence-platform.md`.
