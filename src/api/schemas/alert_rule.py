from __future__ import annotations

import re
from datetime import datetime

from pydantic import BaseModel, EmailStr, field_validator, model_validator
from typing import Literal


class CreateAlertRuleRequest(BaseModel):
    niche_id: str
    threshold_score: float
    delivery_channel: Literal["webhook", "email", "both"]
    webhook_url: str | None = None
    email: EmailStr | None = None

    _BLOCKED_URL_PATTERNS = [
        r'^https?://localhost',
        r'^https?://127\.',
        r'^https?://0\.',
        r'^https?://10\.',
        r'^https?://172\.(1[6-9]|2[0-9]|3[01])\.',
        r'^https?://192\.168\.',
        r'^https?://169\.254\.',  # AWS metadata
    ]

    @field_validator('webhook_url', mode='before')
    @classmethod
    def validate_webhook_url(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if not v.startswith('https://'):
            raise ValueError('webhook_url must use HTTPS')
        for pattern in cls._BLOCKED_URL_PATTERNS:
            if re.match(pattern, v, re.IGNORECASE):
                raise ValueError('webhook_url cannot point to private/internal addresses')
        return v

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
