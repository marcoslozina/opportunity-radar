# Explore: API Keys Layer

## Current State

### How the API works today

The API is a FastAPI application with zero authentication. Every endpoint is publicly accessible without any credential. The middleware stack has exactly one layer: `RequestLoggingMiddleware` (a `BaseHTTPMiddleware` subclass in `src/api/middleware/logging.py`) that logs method, path, status code, and duration — and injects an `X-Request-ID` header. There is no security, no identity, no rate limiting.

Routes are grouped into seven routers:
- `GET/POST /niches` — manage tracked niches (create, list, delete)
- `GET /briefing/{niche_id}` — latest content opportunity briefing
- `GET /product-briefing/{niche_id}` — latest product opportunity briefing
- `GET /opportunities?niche_id=` — paginated opportunity list
- `POST /pipeline/run/{niche_id}` — triggers a background pipeline run
- `GET /keywords/*` — keyword suggestion helpers
- `GET /health` — scheduler status

Dependency injection is entirely manual: each route declares `session: AsyncSession = Depends(get_session)` and instantiates repositories and use cases inline.

### What is missing for external consumers

1. **No identity model.** There is no concept of "who is calling." Every caller gets the same data, the same permissions, and leaves no audit trail.
2. **No access control.** A vertical like PropFlow cannot be scoped to "only its own niches." Today every caller sees every niche.
3. **No rate limiting.** A misbehaving external client can hammer the DB and the Claude API with no throttling.
4. **No API key storage.** There is no `ApiKey` DB model, no domain entity, no port, no repository.
5. **Administrative endpoints are exposed the same as read endpoints.** `POST /pipeline/run`, `POST /niches`, `DELETE /niches/{id}` are write/admin operations that should not be callable by external verticals.

---

## Key Questions

1. **Scope of an API key:** Does a key belong to a *tenant* (e.g. PropFlow the product) and grant access to its specific niches only? Or is it a single global admin key?
2. **Key storage:** DB table (auditable, revocable, expirable) vs environment config (simple, zero migration)?
3. **Transport mechanism:** `X-API-Key` header (industry standard) vs `Authorization: Bearer` (same wire format as JWT, future-proof) vs query param (insecure in logs)?
4. **Which endpoints to expose externally:** Read-only (`/briefing`, `/product-briefing`, `/opportunities`) vs write/trigger operations (`/pipeline/run`, `/niches` CRUD)?
5. **Rate limiting strategy:** Simple per-key request counter with a sliding window vs token bucket vs no rate limiting in v1 and revisit later?
6. **Key provisioning:** Admin CLI command? Dedicated `POST /api-keys` endpoint (itself key-protected)? Manual DB insert?
7. **Hashing:** Store keys hashed (bcrypt/sha256) or in plaintext? Hashed is safer but adds lookup cost.

---

## Technical Findings

### Architecture layers affected

| Layer | File | Finding |
|---|---|---|
| Domain | `src/domain/ports/` | No port exists for key lookup. A new `ApiKeyRepository` port is needed. |
| Infrastructure | `src/infrastructure/db/models.py` | No `ApiKeyModel`. The existing `Base` (SQLAlchemy `DeclarativeBase`) is the right extension point. |
| Infrastructure | `src/infrastructure/db/session.py` | `get_session()` is an async generator yielding `AsyncSession`. This is the pattern to follow for the key-lookup dependency. |
| API | `src/api/middleware/logging.py` | The only middleware is logging. Auth can be added as middleware OR as a FastAPI dependency. |
| API | `src/main.py` | All routers are registered flat — no versioning, no router grouping by access tier. |
| Config | `src/config.py` | `pydantic-settings` is already in use. A single master key could live here for bootstrapping, but per-client keys must be in DB for revocability. |

### FastAPI DI pattern already established

Every route already uses `Depends(get_session)`. FastAPI's dependency system supports chaining — an `authenticate` dependency can itself depend on `get_session` to look up the key in DB, and routes can add it as an additional `Depends(authenticate)`. This is the idiomatic FastAPI pattern and requires zero changes to the middleware or lifespan.

### No existing hashing library

`pyproject.toml` has no `passlib`, `bcrypt`, or `hashlib`-based wrapper. Python's stdlib `hashlib` (SHA-256) is sufficient and zero-dependency for key hashing.

### SQLite in dev, asyncpg for prod

`database_url` defaults to `sqlite+aiosqlite` but `asyncpg` is in dependencies. Key lookups must be async-safe — already guaranteed by the existing session factory.

### Migration path is clear

Alembic is set up with three existing migrations. Adding an `ApiKeyModel` follows the exact same pattern: new model in `models.py`, `alembic revision --autogenerate`.

### Domain applicability field

`OpportunityModel.domain_applicability` already exists (`src/infrastructure/db/models.py` line 72). This confirms the system already has a notion of "which domain/vertical an opportunity is for." An API key tied to a vertical can filter on this field.

---

## Hypothesis

The cleanest approach is a **FastAPI dependency-based authenticator** backed by a new `ApiKeyModel` DB table. A vertical sends `X-API-Key: <key>` in the header. A `get_api_key` dependency hashes the incoming value with SHA-256 and queries the `api_keys` table for a matching, active, non-expired record. If found, it returns an `ApiKeyContext` (caller identity + scopes). Routes that should be protected declare `Depends(get_api_key)`. Admin/write routes (`/pipeline/run`, `POST /niches`, `DELETE /niches`) remain internal-only by keeping them unauthenticated but network-restricted (or behind a separate admin key). Read endpoints (`/briefing`, `/product-briefing`, `/opportunities`) become the public surface for external verticals. This approach requires no new middleware, no new library, follows the existing DI pattern exactly, and is fully auditable and revocable per key.
