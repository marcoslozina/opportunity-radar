# Tasks: API Keys Layer

## Phase 1: Domain

- [ ] **1.1** Create `ApiKey` entity in `src/domain/entities/api_key.py`
  - Fields: `id`, `client_name`, `key_hash`, `scopes`, `active`, `created_at`, `expires_at`
  - Class method `generate(client_name, scopes, expires_at) -> tuple[ApiKey, str]` — returns entity + raw key (shown once)
  - Class method `hash_raw(raw_key: str) -> str` — SHA-256 hex digest, no side effects
  - Instance method `is_valid() -> bool` — checks `active` and `expires_at`
  - Instance method `revoke() -> None` — sets `active = False`
  - Key format: `or_live_` + `secrets.token_urlsafe(32)`

- [ ] **1.2** Create `ApiKeyContext` value object in `src/domain/value_objects/api_key_context.py`
  - Frozen dataclass with fields: `client_name: str`, `scopes: tuple[str, ...]`, `key_id: str`
  - Must be hashable (frozen=True guarantees this)

- [ ] **1.3** Add `ApiKeyRepository` port to `src/domain/ports/repository_ports.py`
  - Abstract methods: `save(api_key: ApiKey)`, `find_by_hash(key_hash: str) -> ApiKey | None`, `revoke(key_id: str)`, `list_all() -> list[ApiKey]`
  - Add import for `ApiKey` entity at top of file

---

## Phase 2: Infrastructure

- [ ] **2.1** Add `ApiKeyModel` to `src/infrastructure/db/models.py`
  - Columns: `id VARCHAR(36) PK`, `client_name VARCHAR(255) NOT NULL INDEX`, `key_hash VARCHAR(64) UNIQUE NOT NULL INDEX`, `scopes_json TEXT NOT NULL DEFAULT '[]'`, `active BOOL NOT NULL DEFAULT TRUE`, `created_at DATETIME`, `expires_at DATETIME NULLABLE`
  - No FK to existing tables
  - Property `scopes` that JSON-decodes `scopes_json` (follow the same pattern as `NicheModel.keywords`)

- [ ] **2.2** Generate and review Alembic migration
  - Run: `alembic revision --autogenerate -m "add_api_keys_table"`
  - Verify generated file: `key_hash` is `UNIQUE`, both `key_hash` and `client_name` have indexes
  - Apply: `alembic upgrade head` in dev

- [ ] **2.3** Implement `SqlApiKeyRepository` in `src/infrastructure/db/repositories.py`
  - Methods: `find_by_hash`, `save`, `revoke`, `list_all`
  - Private `_to_entity(model: ApiKeyModel) -> ApiKey` mapper
  - Follow existing `SQLNicheRepository` pattern for session usage

---

## Phase 3: API Layer

- [ ] **3.1** Create `src/api/dependencies/` directory and `src/api/dependencies/api_key.py`
  - Module-level `TTLCache[str, ApiKeyContext]` with `maxsize=512`, `ttl=300`
  - `get_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key"), session=Depends(get_session), request: Request = ...) -> ApiKeyContext` async function
  - Flow: header present check → SHA-256 hash → cache lookup → DB lookup → active/expiry checks → cache write → set `request.state.api_key_ctx` → return `ApiKeyContext`
  - Raise `HTTPException(401)` with specific `detail` for each failure mode (missing, invalid, revoked, expired)

- [ ] **3.2** Apply `get_api_key` dependency to protected routes
  - `src/api/routes/briefing.py`: add `api_key_ctx: ApiKeyContext = Depends(get_api_key)` to the route function signature
  - `src/api/routes/product_briefing.py`: same
  - `src/api/routes/opportunities.py`: same
  - No changes to `health.py`, `pipeline.py`, `niches.py`, `keywords.py`

- [ ] **3.3** Extend `RequestLoggingMiddleware` in `src/api/middleware/logging.py`
  - After `call_next`, read `client_name` from `request.state.api_key_ctx` if present
  - Add `client=%s` field to the log line (value is `client_name` or `"anonymous"`)
  - Log field order suggestion: `request_id`, `method`, `path`, `client`, `status`, `duration_ms`

- [ ] **3.4** Create `scripts/manage_keys.py` CLI
  - Commands: `create --client <name> --scopes <scope,...> [--expires <ISO-date>]`, `revoke --key-id <uuid>`, `list`
  - `create` prints the raw key exactly once with a clear warning: "Save this key — it will not be shown again"
  - Uses `asyncio.run()` + `AsyncSessionFactory` following the same pattern as `_run_content_pipeline` in `pipeline.py`
  - No external CLI framework needed — stdlib `argparse` is sufficient

---

## Phase 4: Tests

- [ ] **4.1** Unit tests for `ApiKey` entity — `tests/unit/test_api_key_entity.py`
  - `test_generate_returns_raw_key_with_correct_prefix`
  - `test_generate_stores_hash_not_raw_key`
  - `test_hash_raw_is_deterministic`
  - `test_is_valid_returns_false_when_inactive`
  - `test_is_valid_returns_false_when_expired`
  - `test_is_valid_returns_true_when_active_and_no_expiry`
  - `test_revoke_sets_active_false`

- [ ] **4.2** Unit tests for `get_api_key` dependency — `tests/unit/test_auth_dependency.py`
  - Use `fastapi.testclient.TestClient` with `app.dependency_overrides` or build a minimal test app
  - `test_get_api_key_when_header_missing_then_401`
  - `test_get_api_key_when_key_not_found_then_401`
  - `test_get_api_key_when_key_revoked_then_401`
  - `test_get_api_key_when_key_expired_then_401`
  - `test_get_api_key_when_valid_key_then_returns_context`
  - `test_get_api_key_cache_hit_skips_db` (assert repo.find_by_hash not called on second request)

- [ ] **4.3** Integration tests — `tests/integration/test_api_auth.py`
  - Use the existing async test session setup pattern (follow `tests/integration/test_api_briefing.py`)
  - `test_protected_endpoint_with_valid_key_returns_200`
  - `test_protected_endpoint_with_no_key_returns_401`
  - `test_protected_endpoint_with_invalid_key_returns_401`
  - `test_protected_endpoint_with_revoked_key_returns_401`
  - `test_health_endpoint_without_key_returns_200` (smoke test for public routes)

---

## Implementation Order and Dependencies

```
1.1 → 1.2 → 1.3    (domain — no external deps)
        ↓
      2.1 → 2.2 → 2.3    (infra — depends on domain entities)
                    ↓
                  3.1 → 3.2 → 3.3 → 3.4    (API — depends on infra)
                                ↓
                              4.1, 4.2, 4.3  (tests — can run after 3.x)
```

Phases 1 and 2 are fully independent from the existing route code and can be developed without touching any production path. Phase 3 is the only phase that modifies existing files (`briefing.py`, `product_briefing.py`, `opportunities.py`, `logging.py`). Phase 4 can be written alongside Phase 3 in TDD style.

---

## Definition of Done

- [ ] All unit tests pass (`pytest tests/unit/`)
- [ ] All integration tests pass (`pytest tests/integration/`)
- [ ] `ruff check src/` reports no errors
- [ ] `mypy src/` reports no new errors
- [ ] Alembic migration applies and downgrades cleanly
- [ ] `GET /briefing/{niche_id}` returns `401` without `X-API-Key`
- [ ] `GET /briefing/{niche_id}` returns `200` with a valid key created via CLI
- [ ] `GET /health` returns `200` without any key
- [ ] Log lines for authenticated requests include `client=<name>`
