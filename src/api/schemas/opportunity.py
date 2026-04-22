from __future__ import annotations

from pydantic import BaseModel


class OpportunityScoreResponse(BaseModel):
    trend_velocity: float
    competition_gap: float
    social_signal: float
    monetization_intent: float
    total: float
    confidence: str


class OpportunityResponse(BaseModel):
    id: str
    topic: str
    score: OpportunityScoreResponse
    recommended_action: str


class BriefingResponse(BaseModel):
    id: str
    niche_id: str
    opportunities: list[OpportunityResponse]
    generated_at: str
