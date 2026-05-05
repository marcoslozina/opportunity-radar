# Technical Design: Niche Expansion - PropFlow (Real Estate)

## 1. Problem Statement
The current system is designed for general product opportunities. We need to expand it to support specific niches, starting with "PropFlow" (Real Estate Argentina). This requires specialized scoring logic and a more generic way to store domain-specific applicability and reasoning in the `Opportunity` entity.

## 2. Proposed Changes

### 2.1. Domain Layer (`src/domain/entities/opportunity.py`)
- Refactor `Opportunity` to include:
    - `domain_applicability: str` (Represents relevance to the specific niche, e.g., "calculadora", "contenido", "feature", "irrelevante").
    - `domain_reasoning: str` (AI-generated reasoning for the score).
- Default values should ensure backward compatibility with general mode.

### 2.2. Application Layer (Scoring Engine)
- **Generalization**: Modify `ScoringEngine` to support configurable weights for its dimensions.
- **Specialization**: Implement `PropFlowScoringEngine` with weights from Spec:
    - `social_signal`: 0.15
    - `trend_velocity`: 0.15
    - `competition_gap`: 0.20
    - `monetization_intent`: 0.30
    - `frustration_level`: 0.20
- **Factory Pattern**: Create a `ScoringFactory` that selects the appropriate engine based on `Niche.discovery_mode`.

### 2.3. Pipeline Integration (`src/application/use_cases/run_pipeline.py`)
- Update `RunPipelineUseCase` to use the `ScoringFactory` instead of a hardcoded `ScoringEngine`.
- Ensure the selected engine is used to score signals and populate the new `Opportunity` fields.

### 2.4. Infrastructure (Niche Templates)
- Create `src/infrastructure/niche_templates.py` containing the `NicheTemplate` dataclass and `TEMPLATES` dictionary.
- Include "PropFlow" template.

### 2.5. UI Logic (Dashboard)
- Update `dashboard.py` to dynamically display the "Aplicabilidad" column when discovery mode is `real_estate` (PropFlow) or `esg_intelligence`.

## 3. Technical Implementation Details

### File: `src/domain/entities/opportunity.py`
```python
@dataclass
class Opportunity:
    id: OpportunityId
    topic: str
    score: OpportunityScore
    recommended_action: str = field(default="")
    domain_applicability: str = field(default="")
    domain_reasoning: str = field(default="")
```

### File: `src/application/services/scoring_engine.py`
- Subclase `PropFlowScoringEngine` inheriting from `ScoringEngine`.
- Override weights.

## 4. Verification Plan
- **Unit Tests**:
    - `test_propflow_scoring_engine`: Verify weights from spec are applied.
    - `test_scoring_factory`: Verify correct engine selection.
- **Integration Test**:
    - End-to-end run with PropFlow template.
