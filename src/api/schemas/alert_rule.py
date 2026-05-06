from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, field_validator, model_validator
from typing import Literal


class CreateAlertRuleRequest(BaseModel):
    niche_id: str
    threshold_score: float
    delivery_channel: Literal["webhook", "email", "both"]
    webhook_url: str | None = None
    email: str | None = None

    @field_validator("threshold_score")
    @classmethod
    def validate_threshold(cls, v: float) -> float:
        if not 0.0 <= v <= 100.0:
            raise ValueError("threshold_score must be between 0.0 and 100.0")
        return v

    @model_validator(mode="after")
    def validate_channel_fields(self) -> CreateAlertRuleRequest:
        if self.delivery_channel in ("webhook", "both") and not self.webhook_url:
            raise ValueError(
                "webhook_url is required when delivery_channel is 'webhook' or 'both'"
            )
        if self.delivery_channel in ("email", "both") and not self.email:
            raise ValueError(
                "email is required when delivery_channel is 'email' or 'both'"
            )
        return self


class AlertRuleResponse(BaseModel):
    id: str
    niche_id: str
    threshold_score: float
    delivery_channel: str
    webhook_url: str | None
    email: str | None
    active: bool
    last_notified_at: datetime | None
    created_at: datetime
