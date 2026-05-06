from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

KEY_PREFIX = "or_live_"


@dataclass
class ApiKey:
    id: str
    client_name: str
    key_hash: str
    scopes: list[str]
    active: bool
    created_at: datetime
    expires_at: datetime | None
    tier: str = "starter"
    monthly_quota_used: int = 0
    quota_reset_at: datetime | None = None

    @classmethod
    def generate(
        cls,
        client_name: str,
        scopes: list[str],
        expires_at: datetime | None = None,
    ) -> tuple[ApiKey, str]:
        """Factory: returns (entity, raw_key). raw_key is shown once and never stored."""
        raw_key = KEY_PREFIX + secrets.token_urlsafe(32)
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        entity = cls(
            id=str(uuid4()),
            client_name=client_name,
            key_hash=key_hash,
            scopes=scopes,
            active=True,
            created_at=datetime.now(timezone.utc),
            expires_at=expires_at,
        )
        return entity, raw_key

    @classmethod
    def hash_raw(cls, raw_key: str) -> str:
        """Hash an incoming raw key for lookup. Pure function, no side effects."""
        return hashlib.sha256(raw_key.encode()).hexdigest()

    def is_valid(self) -> bool:
        if not self.active:
            return False
        if self.expires_at is not None and self.expires_at < datetime.now(timezone.utc):
            return False
        return True

    def revoke(self) -> None:
        self.active = False
