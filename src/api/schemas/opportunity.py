from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class OpportunityScoreResponse(BaseModel):
    trend_velocity: float
    competition_gap: float
    social_signal: float
    monetization_intent: float
    total: float
    confidence: str


class ScoreTrajectoryResponse(BaseModel):
    previous_total: float
    delta: float
    delta_pct: float
    direction: str
    compared_at: datetime


class EvidenceItemResponse(BaseModel):
    source: str
    signal_type: str
    topic: str
    title: str
    url: str | None
    engagement_count: int
    engagement_label: str
    collected_at: str  # ISO 8601 string — simpler than datetime for JSON clients


class OpportunityResponse(BaseModel):
    id: str
    topic: str
    score: OpportunityScoreResponse
    recommended_action: str
    trajectory: ScoreTrajectoryResponse | None = None
    evidence: list[EvidenceItemResponse] = []


class BriefingResponse(BaseModel):
    id: str
    niche_id: str
    opportunities: list[OpportunityResponse]
    generated_at: str
