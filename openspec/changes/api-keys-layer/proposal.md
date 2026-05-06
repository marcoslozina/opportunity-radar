# Proposal: API Keys Layer

## Context

Opportunity Radar is an internal intelligence engine. PropFlow (and future verticals) need to consume its scored opportunities via authenticated HTTP calls. Today every endpoint is fully open — zero identity, zero access control, zero audit trail. Before any external integration can be built, the API needs a credential layer that:

1. Identifies the calling vertical (who is this?)
2. Controls access (what can they read?)
3. Enables auditing and revocation (per key, not per deployment)
4. Does not break the existing internal tooling (dashboard, scheduler, pipeline triggers)

---

## Option A — FastAPI Dependency-Based Authentication with DB-backed Keys

### How it works

A new `ApiKeyModel` is added to `src/infrastructure/db/models.py` with fields: `key_hash` (SHA-256 of the raw key), `client_name`, `scopes` (JSON list), `active`, `created_at`, `expires_at`. A new domain port `ApiKeyRepository` (ABC) and its SQL implementation `SQLApiKeyRepository` are created following the existing port pattern. A FastAPI dependency `get_api_key(x_api_key: str = Header(...), session = Depends(get_session))` hashes the incoming value and queries the table. If found and active, it returns an `ApiKeyContext` dataclass (client name + scopes). Routes that should be externally accessible declare `Depends(get_api_key)` in their signature — nothing else changes. Admin/write routes remain undeclared (no key dep) and are protected at the network layer (internal only). Key provisioning is done via a CLI management script (`scripts/manage_keys.py`) that inserts hashed keys into the DB.

```
X-API-Key: or-live-<random-32-bytes-hex>
                        |
                   SHA-256 hash
                        |
              api_keys table lookup
                        |
              ApiKeyContext(client="propflow", scopes=["read:briefing"])
                        |
              route handler proceeds
```

### Advantages
- Follows the EXACT same DI pattern already in every route (`Depends(...)`) — zero conceptual overhead
- Fully revocable per key (set `active=False`)
- Expiry supported natively via `expires_at`
- Auditable: know which client called, when, via existing `RequestLoggingMiddleware` (extend log line with `client_name`)
- No new library needed — SHA-256 is Python stdlib `hashlib`
- Scopes allow future granularity (e.g., `read:briefing`, `read:product-briefing`, `write:pipeline`)
- Alembic migration is straightforward (one new table)
- Keys are never stored in plaintext — only the hash lives in DB

### Disadvantages
- Requires an Alembic migration (minor, already established pattern)
- Every protected request does one DB lookup — adds ~1-3ms latency per call (acceptable; can cache with `cachetools` which is already in `pyproject.toml`)
- No self-service key provisioning (requires CLI or admin access to generate keys)

### Best when
- You need per-client identity and revocability
- Multiple verticals will integrate over time
- You want an audit trail of who called what
- This is the production path, not a quick prototype

---

## Option B — Static Key from Environment Config

### How it works

A single `api_key: str = ""` field is added to the `Settings` class in `src/config.py` (already a `pydantic-settings` instance). A FastAPI dependency reads `settings.api_key` and compares it to the incoming `X-API-Key` header using `secrets.compare_digest`. If they match, the request proceeds. No DB model, no migration, no repository. One key for all callers. Key rotation means a redeploy.

```
X-API-Key: <value>
                  |
          secrets.compare_digest(value, settings.api_key)
                  |
          pass / 401
```

### Advantages
- Zero new files — two lines added to `config.py` and a small dependency function
- No DB migration
- No latency overhead (in-memory comparison)
- Dead simple to understand and audit

### Disadvantages
- Single key = all verticals share the same credential — cannot revoke PropFlow without revoking everyone
- Key lives in `.env` — rotation requires redeploy
- No audit trail per client (all calls look the same)
- Scopes are binary (in/out), no granularity
- Does not scale beyond one caller

### Best when
- You have exactly one external consumer and plan to keep it that way
- This is a short-lived prototype (days/weeks, not months)
- You need the fastest possible path to unblock integration work

---

## Recommended Option

**Option A — FastAPI Dependency with DB-backed Keys.**

The technical reasoning is concrete: `cachetools` is already in `pyproject.toml` (so the "one DB lookup per request" concern is trivially solved with a short-lived in-memory cache of hashed-key → `ApiKeyContext`). Alembic is already set up with a proven migration pattern. The port + repository pattern is already the codebase convention, so `ApiKeyRepository` is not new infrastructure — it's following the existing architectural contract. And critically, PropFlow is the first vertical but not the last — the ESG niche, the real estate niche, and future products will each want their own key, their own revocability, and their own audit trail.

Option B is tempting for its simplicity, but it creates a ceiling: the first time a second vertical needs to integrate, or the first time a key is compromised, Option B must be thrown away and A built from scratch. Building A now avoids that rework.

---

## Scope

### In scope
- New `ApiKeyModel` in `src/infrastructure/db/models.py`
- New Alembic migration for `api_keys` table
- New domain port `ApiKeyRepository` in `src/domain/ports/`
- New `ApiKeyContext` value object in `src/domain/value_objects/`
- New `SQLApiKeyRepository` in `src/infrastructure/db/`
- New `get_api_key` FastAPI dependency in `src/api/dependencies/auth.py`
- Protect read endpoints: `GET /briefing/{niche_id}`, `GET /product-briefing/{niche_id}`, `GET /opportunities`
- Key provisioning CLI script: `scripts/manage_keys.py` (generate + revoke)
- Extend `RequestLoggingMiddleware` to log `client_name` from `ApiKeyContext` when present
- Unit tests for the `get_api_key` dependency (valid key, expired key, revoked key, missing header)
- Integration test hitting a protected endpoint with a valid key

### Out of scope
- Self-service key management UI or API endpoint (manual CLI only for now)
- Per-endpoint scope enforcement (keys are valid for all read endpoints in v1)
- Rate limiting (identified as next phase — see risks)
- Protecting admin/write endpoints (`POST /niches`, `DELETE /niches`, `POST /pipeline/run`) — these remain network-restricted internal routes
- JWT / OAuth2 token exchange (future if multi-user self-service is needed)
- Key rotation automation

---

## Affected Files (estimated)

| File | Change type |
|---|---|
| `src/infrastructure/db/models.py` | Add `ApiKeyModel` |
| `src/domain/ports/repository_ports.py` | Add `ApiKeyRepository` ABC (or new file `api_key_port.py`) |
| `src/domain/value_objects/api_key_context.py` | New — `ApiKeyContext` frozen dataclass |
| `src/infrastructure/db/repositories.py` | Add `SQLApiKeyRepository` (or new file) |
| `src/api/dependencies/` | New directory — `auth.py` with `get_api_key` dependency |
| `src/api/routes/briefing.py` | Add `Depends(get_api_key)` |
| `src/api/routes/opportunities.py` | Add `Depends(get_api_key)` |
| `src/api/routes/product_briefing.py` | Add `Depends(get_api_key)` |
| `src/api/middleware/logging.py` | Extend log line with `client_name` (optional, low risk) |
| `alembic/versions/<hash>_add_api_keys.py` | New migration |
| `scripts/manage_keys.py` | New CLI for key generation and revocation |
| `tests/unit/test_auth_dependency.py` | New unit tests |
| `tests/integration/test_api_auth.py` | New integration tests |
