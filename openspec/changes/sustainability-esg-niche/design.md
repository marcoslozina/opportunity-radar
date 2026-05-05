# Technical Design: Niche Expansion - ESG & Sustainability LATAM

## 1. Problem Statement
Expansion of the opportunity radar to the ESG/Sustainability domain in LATAM. This niche requires a specialized scoring engine that prioritizes frustration signals and competition gaps to identify opportunities for the `sustainability-rag-agent` platform.

## 2. Proposed Changes

### 2.1. Domain Layer
- Uses the generalized `domain_applicability` and `domain_reasoning` fields in the `Opportunity` entity (added in Inmobiliario change).

### 2.2. Application Layer (Scoring Engine)
- **Specialization**: Implement `ESGScoringEngine` with weights from Spec:
    - `social_signal`: 0.10
    - `trend_velocity`: 0.15
    - `competition_gap`: 0.30
    - `monetization_intent`: 0.20
    - `frustration_level`: 0.25
- **Factory Pattern**: Add case to `ScoringFactory` for `esg_intelligence` mode.

### 2.3. Pipeline Integration
- Ensure `RunPipelineUseCase` routes to `ESGScoringEngine` when `discovery_mode == "esg_intelligence"`.

### 2.4. Infrastructure (Niche Templates)
- Add "ESG & Sustainability LATAM" template to `src/infrastructure/niche_templates.py`.

### 2.5. UI Logic (Dashboard)
- Dashboard table shows "Implicación" (using `domain_applicability`) for ESG mode.

## 3. Technical Implementation Details

### File: `src/application/services/scoring_engine.py`
- Subclase `ESGScoringEngine`.
- Config specific weights.

### File: `src/infrastructure/niche_templates.py`
- Add `esg_latam` entry.

## 4. Verification Plan
- **Unit Tests**:
    - `test_esg_scoring_engine`: Verify weights.
- **Integration Test**:
    - Full pipeline run with "ESG LATAM" template.
