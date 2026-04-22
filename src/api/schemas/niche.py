from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, field_validator

DiscoveryMode = Literal["content", "product", "both"]


class CreateNicheRequest(BaseModel):
    name: str
    keywords: list[str]
    discovery_mode: DiscoveryMode = "content"

    @field_validator("keywords")
    @classmethod
    def keywords_not_empty(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("keywords must not be empty")
        return v


class NicheResponse(BaseModel):
    id: str
    name: str
    keywords: list[str]
    active: bool
    discovery_mode: str
