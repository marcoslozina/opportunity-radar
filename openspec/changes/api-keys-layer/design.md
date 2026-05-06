# Design: API Keys Layer

## Architecture Overview

```
External Caller (PropFlow)
        |
        |  X-API-Key: or_live_<token>
        v
  FastAPI Route Handler
        |
        |  Depends(get_api_key)
        v
  ┌─────────────────────────────────────────────────┐
  │              get_api_key dependency              │
  │                                                 │
  │  1. SHA-256(raw_key) → key_hash                 │
  │  2. TTLCache.get(key_hash) → ApiKeyContext?      │
  │       hit ──────────────────────────────────►   │
  │       miss                                      │
  │        │                                        │
  │        v                                        │
  │  SqlApiKeyRepository.find_by_hash(key_hash)     │
  │        │                                        │
  │        ├─ None          → 401 Invalid           │
  │        ├─ active=False  → 401 Revoked           │
  │        ├─ expired       → 401 Expired           │
  │        └─ valid         → ApiKeyContext          │
  │                               │                 │
  │                    TTLCache.set(key_hash, ctx)   │
  │                               │                 │
  └───────────────────────────────┼─────────────────┘
                                  │
                                  v
                          Route handler
                    (receives ApiKeyContext)
                                  │
                                  v
                    RequestLoggingMiddleware
                    logs client_name from
                    request.state.api_key_ctx
```

**Key invariant:** the raw key never touches the DB or the cache. Only its SHA-256 hex digest is stored and looked up.

---

## Domain Layer Changes

### New Value Object: `ApiKeyContext`

File: `src/domain/value_objects/api_key_context.py`

```python
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class ApiKeyContext:
    client_name: str
    scopes: tuple[str, ...]
    key_id: str        # UUID string — for logging / audit
```

- Frozen dataclass: immutable once created, hashable, safe to cache.
- `scopes` is a `tuple` (not `list`) to preserve hashability.
- `key_id` allows correlating a log line to a specific DB record without exposing the hash.

### New Entity: `ApiKey`

File: `src/domain/entities/api_key.py`

```python
from __future__ import annotations
import hashlib
import secrets
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

KEY_PREFIX = "or_live_"

@dataclass
class ApiKey:
    id: str                        # UUID string
    client_name: str
    key_hash: str                  # SHA-256 hex digest of raw key
    scopes: list[str]
    active: bool
    created_at: datetime
    expires_at: datetime | None

    @classmethod
    def generate(cls, client_name: str, scopes: list[str], expires_at: datetime | None = None) -> tuple[ApiKey, str]:
        """Factory: returns (entity, raw_key). raw_key is shown once and never stored."""
        raw_key = KEY_PREFIX + secrets.token_urlsafe(32)
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        entity = cls(
            id=str(uuid4()),
            client_name=client_name,
            key_hash=key_hash,
            scopes=scopes,
            active=True,
            created_at=datetime.utcnow(),
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
        if self.expires_at is not None and self.expires_at < datetime.utcnow():
            return False
        return True

    def revoke(self) -> None:
        self.active = False
```

**Invariants:**
- `generate()` is the only constructor — enforces key format and hashing discipline.
- `hash_raw()` is a pure static-equivalent class method — no coupling to storage or network.
- `is_valid()` encapsulates the active+expiry rule in one place.

### New Port: `ApiKeyRepository`

File: `src/domain/ports/repository_ports.py` (appended to existing file)

```python
class ApiKeyRepository(ABC):
    @abstractmethod
    async def save(self, api_key: ApiKey) -> None: ...

    @abstractmethod
    async def find_by_hash(self, key_hash: str) -> ApiKey | None: ...

    @abstractmethod
    async def revoke(self, key_id: str) -> None: ...

    @abstractmethod
    async def list_all(self) -> list[ApiKey]: ...
```

---

## Infrastructure Layer Changes

### New DB Model: `ApiKeyModel`

File: `src/infrastructure/db/models.py` (append to existing)

```python
class ApiKeyModel(Base):
    __tablename__ = "api_keys"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    client_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    key_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    scopes_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
```

**Index strategy:**
- `key_hash` has a `UNIQUE` constraint + index — every auth lookup is a single O(log n) B-tree lookup on a 64-char hex string.
- `client_name` index supports `list_all()` and future per-client analytics queries.
- No FK to any existing table — API keys are a standalone concern.

**Alembic migration note:** Run `alembic revision --autogenerate -m "add_api_keys_table"`. The migration is purely additive — no `ALTER` on existing tables. Safe to apply with zero downtime. Review autogenerated migration to confirm `key_hash` gets `unique=True` and the index on both columns.

### New Adapter: `SqlApiKeyRepository`

File: `src/infrastructure/db/repositories.py` (appended) or `src/infrastructure/db/api_key_repository.py` (new file if size warrants)

```python
from __future__ import annotations
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from domain.entities.api_key import ApiKey
from domain.ports.repository_ports import ApiKeyRepository
from infrastructure.db.models import ApiKeyModel

class SqlApiKeyRepository(ApiKeyRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_by_hash(self, key_hash: str) -> ApiKey | None:
        result = await self._session.execute(
            select(ApiKeyModel).where(ApiKeyModel.key_hash == key_hash)
        )
        row = result.scalar_one_or_none()
        return self._to_entity(row) if row else None

    async def save(self, api_key: ApiKey) -> None:
        model = ApiKeyModel(
            id=api_key.id,
            client_name=api_key.client_name,
            key_hash=api_key.key_hash,
            scopes_json=json.dumps(api_key.scopes),
            active=api_key.active,
            created_at=api_key.created_at,
            expires_at=api_key.expires_at,
        )
        self._session.add(model)
        await self._session.commit()

    async def revoke(self, key_id: str) -> None:
        result = await self._session.execute(
            select(ApiKeyModel).where(ApiKeyModel.id == key_id)
        )
        row = result.scalar_one_or_none()
        if row:
            row.active = False
            await self._session.commit()

    async def list_all(self) -> list[ApiKey]:
        result = await self._session.execute(select(ApiKeyModel))
        return [self._to_entity(r) for r in result.scalars().all()]

    @staticmethod
    def _to_entity(model: ApiKeyModel) -> ApiKey:
        import json
        return ApiKey(
            id=model.id,
            client_name=model.client_name,
            key_hash=model.key_hash,
            scopes=json.loads(model.scopes_json),
            active=model.active,
            created_at=model.created_at,
            expires_at=model.expires_at,
        )
```

### Cache Layer

File: `src/api/dependencies/api_key.py`

```python
from cachetools import TTLCache
_key_cache: TTLCache[str, ApiKeyContext] = TTLCache(maxsize=512, ttl=300)
```

**Configuration:**
- `maxsize=512`: supports up to 512 distinct active keys in memory — more than sufficient for the near-term client count.
- `ttl=300` (5 minutes): a revoked key is rejected within 5 minutes without requiring cache invalidation logic. Acceptable lag for a revocation event.
- Cache key: the SHA-256 hex digest of the raw incoming key (already computed for DB lookup — no extra work).
- Cache value: `ApiKeyContext` (frozen dataclass — safe to share across requests).
- Thread safety: `TTLCache` is NOT thread-safe. FastAPI runs async (single-threaded event loop in CPython), so concurrent coroutines are fine. If the app is ever run with multiple threads (e.g., `--workers 4` on uvicorn with `--loop asyncio`), wrap cache access in `threading.Lock`. Document this risk explicitly.

---

## Application Layer Changes

None. Authentication is a cross-cutting infrastructure/API concern. The application use cases (RunPipelineUseCase, etc.) remain unaware of API keys. The `ApiKeyContext` is consumed only at the API boundary layer.

---

## API Layer Changes

### New Dependency: `get_api_key`

File: `src/api/dependencies/api_key.py`

Full flow:

```python
from __future__ import annotations
from datetime import datetime
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from cachetools import TTLCache
from domain.entities.api_key import ApiKey
from domain.value_objects.api_key_context import ApiKeyContext
from infrastructure.db.repositories import SqlApiKeyRepository
from infrastructure.db.session import get_session

_key_cache: TTLCache[str, ApiKeyContext] = TTLCache(maxsize=512, ttl=300)

async def get_api_key(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    session: AsyncSession = Depends(get_session),
) -> ApiKeyContext:
    if x_api_key is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="X-API-Key header missing")

    key_hash = ApiKey.hash_raw(x_api_key)

    cached = _key_cache.get(key_hash)
    if cached is not None:
        return cached

    repo = SqlApiKeyRepository(session)
    api_key = await repo.find_by_hash(key_hash)

    if api_key is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
    if not api_key.active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API key has been revoked")
    if api_key.expires_at is not None and api_key.expires_at < datetime.utcnow():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API key has expired")

    ctx = ApiKeyContext(
        client_name=api_key.client_name,
        scopes=tuple(api_key.scopes),
        key_id=api_key.id,
    )
    _key_cache[key_hash] = ctx
    return ctx
```

**Error response policy:** all 401 responses use a consistent `{"detail": "<reason>"}` shape. The reason is human-readable but does not leak the hash, DB state, or internal structure.

### Route Changes

Routes that gain `Depends(get_api_key)`:

| Route file | Endpoint | Change |
|---|---|---|
| `src/api/routes/briefing.py` | `GET /briefing/{niche_id}` | Add `api_key_ctx: ApiKeyContext = Depends(get_api_key)` |
| `src/api/routes/product_briefing.py` | `GET /product-briefing/{niche_id}` | Add `api_key_ctx: ApiKeyContext = Depends(get_api_key)` |
| `src/api/routes/opportunities.py` | `GET /opportunities` | Add `api_key_ctx: ApiKeyContext = Depends(get_api_key)` |

Routes that remain public (no change):

| Route file | Endpoints |
|---|---|
| `src/api/routes/health.py` | `GET /health` |
| `src/api/routes/niches.py` | `GET/POST/DELETE /niches/*` |
| `src/api/routes/pipeline.py` | `POST /pipeline/run/{niche_id}` |
| `src/api/routes/keywords.py` | `GET /keywords/*` |

### Middleware Extension

File: `src/api/middleware/logging.py`

The `RequestLoggingMiddleware` cannot directly access FastAPI dependency results (they run inside the route, not in middleware). The recommended pattern is to set `request.state.api_key_ctx` inside `get_api_key` before returning, then read it in the middleware after `call_next`:

```python
# In get_api_key dependency — after ctx is resolved:
# request.state.api_key_ctx = ctx  ← requires passing Request as a param

# In middleware:
client_name = getattr(request.state, "api_key_ctx", None)
client_name_str = client_name.client_name if client_name else "anonymous"
logger.info("... client=%s ...", client_name_str)
```

**Alternative:** log `client_name` inside the route handler itself using the `api_key_ctx` parameter. This is simpler but means admin/public routes are not logged uniformly. The `request.state` approach is preferred for uniformity.

### New Management Routes (v1 — CLI only, no HTTP endpoint)

In v1, key provisioning is handled by `scripts/manage_keys.py` (CLI). No `POST /admin/api-keys` HTTP endpoint is created in this phase to avoid exposing a key-creation surface before proper admin authentication is in place.

The CLI script:
```
python scripts/manage_keys.py create --client propflow --scopes read:opportunities
# Prints: API Key (save this, it will not be shown again):
#   or_live_<token>

python scripts/manage_keys.py revoke --key-id <uuid>
python scripts/manage_keys.py list
```

---

## Security Considerations

### Key format

```
or_live_<32-bytes-base64url>
```

- `or_live_` prefix: identifies the issuer and environment at a glance, matches the convention shown in the proposal (`or-live-<hex>` — slightly adjusted to use underscore separator for readability).
- `secrets.token_urlsafe(32)` generates 32 bytes of cryptographic randomness encoded as ~43 URL-safe base64 characters. Entropy: 256 bits. Brute-forcing is computationally infeasible.
- Total key length: ~51 characters. Fits comfortably in an HTTP header.

### Key storage

- Only `SHA-256(raw_key).hexdigest()` is stored in the DB — a 64-char hex string.
- SHA-256 is used instead of bcrypt because API keys are high-entropy random strings (not passwords). The entropy of the key itself prevents rainbow-table attacks, so bcrypt's cost factor adds latency without meaningful security gain. This is standard practice (Stripe, GitHub use SHA-256 for API key storage).
- The raw key is shown to the operator exactly once (in the CLI create output) and never stored anywhere.

### Timing safety

- All 401 responses should be returned in constant time to prevent timing oracle attacks. The dependency always computes `SHA-256(raw_key)` before any conditional — this ensures consistent timing regardless of whether the key exists or not. For the DB hit/miss case, consider a constant-time comparison of the hash string using `hmac.compare_digest` when comparing the looked-up hash to the input hash (though since the lookup is by equality in SQL, this is a secondary concern).

### Log safety

- The raw `X-API-Key` header value MUST NOT appear in any log line. The `RequestLoggingMiddleware` logs `path`, `method`, `status`, `duration`, and `client_name` — not the key value. FastAPI's default exception handler also does not echo request headers.

---

## Migration Strategy

1. Add `ApiKeyModel` to `src/infrastructure/db/models.py`.
2. Run `alembic revision --autogenerate -m "add_api_keys_table"` — generates the migration file.
3. Review the generated file: confirm `key_hash` is `VARCHAR(64) UNIQUE NOT NULL` with an index, and `client_name` has an index.
4. Run `alembic upgrade head` in all environments.
5. The new `api_keys` table is empty — all existing endpoints continue to work as before (protected routes are not yet protected until code is deployed).
6. Generate at least one key for PropFlow via the CLI before deploying the route dependency changes.
7. Deploy the route dependency changes — protected routes now require `X-API-Key`.

**Rollback plan:** The Alembic migration is purely additive. Rolling back means running `alembic downgrade -1` (drops the `api_keys` table) and reverting the route dependency code. No data in existing tables is touched.
