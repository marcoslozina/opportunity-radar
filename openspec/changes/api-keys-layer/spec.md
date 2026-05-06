# Spec: API Keys Layer

## Goal

Add a per-client, DB-backed API key authentication layer to Opportunity Radar so that external verticals (PropFlow and future consumers) can securely access read endpoints with a revocable, scoped credential.

---

## Requirements

### Functional

- **FR-1 Key Creation:** The system MUST be able to generate a new API key for a named client. Generation produces a raw key (returned once, never stored) and persists only its SHA-256 hash + metadata to the `api_keys` table.
- **FR-2 Key Validation:** On every protected request the system MUST verify the `X-API-Key` header. Verification hashes the incoming value with SHA-256 and performs a lookup against the `api_keys` table (cache-first, DB-fallback).
- **FR-3 Key Revocation:** An operator MUST be able to revoke a key by setting `active = False` on the corresponding record. Revoked keys are rejected immediately (cache is bypassed on active=False records or TTL naturally expires within 5 minutes).
- **FR-4 Key Expiry:** Keys MAY carry an `expires_at` timestamp. The validation path MUST reject keys whose `expires_at` is in the past. Keys with `expires_at = NULL` are considered non-expiring.
- **FR-5 Vertical Scoping:** Each key carries a `scopes` field (JSON list of strings). In v1 the only enforced scope is `read:opportunities` (grants access to all three read endpoints). Future scopes (`read:briefing`, `write:pipeline`) are reserved but not enforced yet.
- **FR-6 Protected Endpoints:** The following endpoints MUST require a valid API key:
  - `GET /briefing/{niche_id}`
  - `GET /product-briefing/{niche_id}`
  - `GET /opportunities`
- **FR-7 Public Endpoints:** The following endpoints MUST remain publicly accessible without any credential:
  - `GET /health`
  - All `/pipeline/*` routes (internal, network-restricted)
  - All `/niches/*` routes (internal, network-restricted)
  - All `/keywords/*` routes (internal, network-restricted)
- **FR-8 Key Provisioning:** A CLI script (`scripts/manage_keys.py`) MUST allow operators to generate and revoke keys without direct DB access.
- **FR-9 Audit Trail:** The `RequestLoggingMiddleware` MUST be extended to include `client_name` in the log line when a request carries a valid API key, enabling per-client audit from existing logs.
- **FR-10 Rate Limiting (v1 — minimal):** Not enforced in v1. The spec records the intent so the next phase can add a sliding-window counter per `key_hash`.

### Non-Functional

- **NFR-1 Auth overhead < 5 ms (cache-hit path):** The TTL cache lookup + SHA-256 hash of the incoming key must complete in under 5 ms. SHA-256 on a 64-byte key is ~0.01 ms; `cachetools.TTLCache` dict lookup is O(1). This is feasible without further optimization.
- **NFR-2 Auth overhead < 10 ms (DB-fallback path):** A single indexed `SELECT` on `key_hash` against SQLite (dev) or Postgres (prod) with a VARCHAR(64) index must complete under 10 ms under normal load.
- **NFR-3 No plaintext key storage:** The raw API key MUST never be persisted anywhere — not in the DB, not in logs, not in responses (except the single creation response, displayed once).
- **NFR-4 Backward compatibility:** All currently non-protected endpoints MUST continue to work without any credential after this change is deployed.
- **NFR-5 Zero-downtime migration:** The Alembic migration is purely additive (new table, no changes to existing tables). It can be applied while the app is running.
- **NFR-6 Testability:** The `get_api_key` dependency MUST be overridable via FastAPI's `app.dependency_overrides` mechanism in tests — no global state, no singletons that cannot be replaced.

---

## Scenarios (Given / When / Then)

### Scenario 1: Valid key — happy path

Given a client has a valid, active, non-expired API key `or_live_<token>`  
And the key hash exists in the `api_keys` table with `active = True` and `expires_at = NULL`  
When the client sends `GET /briefing/{niche_id}` with header `X-API-Key: or_live_<token>`  
Then the response status is `200 OK`  
And the `ApiKeyContext` with `client_name = "propflow"` is available to the route handler  
And the log line includes `client_name=propflow`

### Scenario 2: Missing header

Given no `X-API-Key` header is present in the request  
When the client sends `GET /briefing/{niche_id}`  
Then the response status is `401 Unauthorized`  
And the response body is `{"detail": "X-API-Key header missing"}`

### Scenario 3: Invalid key (unknown hash)

Given a client sends an arbitrary string that does not match any `key_hash` in the DB  
When the client sends `GET /briefing/{niche_id}` with header `X-API-Key: invalid-garbage`  
Then the response status is `401 Unauthorized`  
And the response body is `{"detail": "Invalid API key"}`  
And no sensitive information (hash, DB error) is leaked in the response

### Scenario 4: Revoked key

Given a key exists in the DB with `active = False`  
When the client sends a request with that key in `X-API-Key`  
Then the response status is `401 Unauthorized`  
And the response body is `{"detail": "API key has been revoked"}`

### Scenario 5: Expired key

Given a key exists in the DB with `active = True` and `expires_at` in the past  
When the client sends a request with that key in `X-API-Key`  
Then the response status is `401 Unauthorized`  
And the response body is `{"detail": "API key has expired"}`

### Scenario 6: Cache hit path

Given a valid key was verified against the DB within the last 5 minutes  
And the `ApiKeyContext` is present in the TTL cache under the key's SHA-256 hash  
When the same client sends another request with the same key  
Then the DB is NOT queried  
And the response status is `200 OK`  
And total auth overhead is under 5 ms

### Scenario 7: Key scoped to specific niche (v1 — pass-through)

Given a key with `scopes = ["read:opportunities"]`  
When the client accesses any of the three protected read endpoints  
Then the request is allowed (v1: no per-endpoint scope enforcement)  
And the `ApiKeyContext.scopes` is available for future enforcement without code changes to the domain

### Scenario 8: Unprotected endpoint accessed without key

Given the client sends `GET /health` with no `X-API-Key` header  
Then the response status is `200 OK`  
And no auth check is performed

---

## Out of Scope

- OAuth2 / JWT token exchange (future — self-service multi-user)
- Per-endpoint scope enforcement beyond `read:opportunities` (v1: all read endpoints share one scope gate)
- Rate limiting per key (next phase — sliding window counter)
- Self-service key management UI or REST endpoint (manual CLI only in v1)
- Multi-tenant data isolation (all keys see all niches in v1)
- Key rotation automation
- Multi-tenant billing
