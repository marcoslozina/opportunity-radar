from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ApiKeyContext:
    client_name: str
    scopes: tuple[str, ...]
    key_id: str  # UUID string — for logging / audit
    tier: str = "starter"
