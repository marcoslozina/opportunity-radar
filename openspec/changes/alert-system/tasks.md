# Tasks: Alert System

## Phase 1 — Domain
Tasks in this phase are independent and can be implemented in any order.

### Task 1.1 — AlertRule entity
- **File:** `src/domain/entities/alert_rule.py` (create)
- Implement `AlertRuleId` (frozen dataclass wrapping UUID) and `AlertRule` dataclass.
- Fields: `id`, `niche_id`, `threshold_score`, `delivery_channel`, `webhook_url`, `email`, `active`, `last_notified_at`, `created_at`.
- `AlertRule.create(...)` factory classmethod.
- Complexity: XS

### Task 1.2 — AlertPayload value object
- **File:** `src/domain/value_objects/alert_payload.py` (create)
- Frozen dataclass with all notification payload fields (see design.md §1.2).
- No external dependencies.
- Complexity: XS

### Task 1.3 — Extend NotificationPort
- **File:** `src/domain/ports/notification_port.py` (modify)
- Add `@abstractmethod async def send_alert(self, payload: AlertPayload) -> bool`.
- Import `AlertPayload` under `TYPE_CHECKING` guard.
- Keep `send_briefing` unchanged — backward compatible.
- Complexity: XS

### Task 1.4 — Add AlertRuleRepository port
- **File:** `src/domain/ports/repository_ports.py` (modify)
- Append `AlertRuleRepository(ABC)` with methods: `save`, `find_by_id`, `find_active_by_niche`, `deactivate`, `list_all`.
- Import `AlertRule`, `AlertRuleId` at the top of the file.
- Complexity: XS

---

## Phase 2 — Infrastructure: DB
Tasks 2.1 and 2.2 can be done in parallel. Task 2.3 depends on 2.1.

### Task 2.1 — AlertRuleModel
- **File:** `src/infrastructure/db/models.py` (modify)
- Append `AlertRuleModel(Base)` class (see design.md §2.1).
- Add composite index `ix_alert_rules_niche_id_active` on `(niche_id, active)`.
- Complexity: S

### Task 2.2 — Alembic migration
- **File:** `alembic/versions/{hash}_add_alert_rules_table.py` (create via `alembic revision --autogenerate -m "add alert_rules table"`)
- Verify generated migration matches design.md §2.2.
- Add index in upgrade(); drop in downgrade().
- Complexity: S

### Task 2.3 — SqlAlertRuleRepository
- **File:** `src/infrastructure/db/repositories.py` (modify)
- Append `SqlAlertRuleRepository` implementing `AlertRuleRepository` port.
- Methods: `save` (merge + flush), `find_by_id` (get by PK), `find_active_by_niche` (select where niche_id + active=True), `deactivate` (update active=False), `list_all` (optional niche_id filter).
- Mapping helpers: `_to_model(rule) -> AlertRuleModel` and `_to_entity(model) -> AlertRule`.
- Complexity: M
- **Depends on:** 2.1

---

## Phase 3 — Infrastructure: Adapters
Tasks 3.1 and 3.2 are independent.

### Task 3.1 — WebhookNotificationAdapter
- **File:** `src/infrastructure/adapters/webhook_notification.py` (create)
- Implement `NotificationPort` (add `send_alert` + no-op `send_briefing`).
- Add concrete `send_alert_to(payload: AlertPayload, webhook_url: str) -> bool`.
- Uses `httpx.AsyncClient` with 10s timeout.
- Catch all exceptions, log at ERROR, return False on failure.
- Complexity: S

### Task 3.2 — ResendEmailAdapter: add send_alert support
- **File:** `src/infrastructure/adapters/resend_email.py` (modify)
- Implement `send_alert(self, payload: AlertPayload) -> bool` — raises `NotImplementedError` (callers must use `send_alert_to_email`; or implement routing here if preferred).
- Add concrete `send_alert_to_email(payload: AlertPayload, email: str) -> bool`.
- Add `_render_alert_html(payload: AlertPayload) -> str` — simple HTML template with niche name, opportunity topic, score, trajectory, domain_applicability, recommended_action.
- Subject format: `[Opportunity Radar] Alert: {niche_name} — score {score}`.
- Complexity: S

---

## Phase 4 — Application
Tasks in this phase are sequential: 4.1 must be complete before 4.2.

### Task 4.1 — AlertEvaluationService
- **File:** `src/application/services/alert_evaluation_service.py` (create)
- Constructor: `alert_rule_repo`, `briefing_repo`, `webhook_adapter`, `email_adapter`.
- `evaluate(briefing: Briefing, niche: Niche) -> None`:
  1. Load active rules for niche via `find_active_by_niche`.
  2. Get previous briefing via `briefing_repo.get_previous(niche.id)`.
  3. Find `top_opp = max(opportunities, key=score.total)`.
  4. For each rule: check threshold, check suppression window (60 min), build `AlertPayload`, dispatch, update `last_notified_at`.
- `_dispatch(rule, payload)`: routes to webhook and/or email based on `delivery_channel`.
- `_compute_trajectory(topic, current_briefing, previous_briefing)`: returns `ScoreTrajectory | None`.
- Wrap each rule evaluation in `try/except Exception` — log and continue.
- Complexity: M

### Task 4.2 — Hook scheduler post-pipeline
- **File:** `src/infrastructure/scheduler/pipeline_scheduler.py` (modify)
- Capture return value of `use_case.execute(...)` as `briefing`.
- After the `execute` call, add a `try/except` block that instantiates `AlertEvaluationService` and calls `await alert_service.evaluate(briefing, niche)`.
- Load niche from `SQLNicheRepository` (session already available).
- Wrap entirely in `try/except Exception` with `logger.error(... non-fatal ...)`.
- Complexity: S
- **Depends on:** 4.1

---

## Phase 5 — API
Tasks in this phase are sequential: 5.1 must be complete before 5.2.

### Task 5.1 — AlertRule API schemas
- **File:** `src/api/schemas/alert_rule.py` (create)
- `CreateAlertRuleRequest(BaseModel)`: `niche_id`, `threshold_score`, `delivery_channel` (Literal), `webhook_url | None`, `email | None`.
- Field validators: `threshold_score` range [0, 100]; `webhook_url` required if channel is webhook/both; `email` required if channel is email/both.
- `AlertRuleResponse(BaseModel)`: all `AlertRule` fields as serializable types.
- Complexity: S

### Task 5.2 — AlertRule router
- **File:** `src/api/routes/alert_rules.py` (create)
- `POST /alert-rules` → create rule, validate niche exists, return 201 `AlertRuleResponse`.
- `GET /alert-rules` → list rules, optional `?niche_id=` query param, return 200 `list[AlertRuleResponse]`.
- `DELETE /alert-rules/{id}` → call `deactivate`, return 204.
- Inject `SqlAlertRuleRepository` via `Depends(get_session)` pattern.
- Protect with existing API key middleware.
- **File:** `src/api/main.py` or app factory — register `alert_rules.router` with prefix `/alert-rules`.
- Complexity: M
- **Depends on:** 5.1, 2.3

---

## Phase 6 — Tests

### Task 6.1 — Unit tests: AlertEvaluationService
- **File:** `tests/unit/test_alert_evaluation_service.py` (create)
- Use fake repositories and fake adapters (no mocking framework — manual fakes per lang-python skill).
- Scenarios to cover:
  - `test_evaluate_fires_when_score_above_threshold`
  - `test_evaluate_does_not_fire_when_all_scores_below_threshold`
  - `test_evaluate_suppresses_when_last_notified_within_1h`
  - `test_evaluate_fires_when_suppression_window_expired`
  - `test_evaluate_skips_inactive_rules`
  - `test_evaluate_continues_when_one_rule_dispatch_fails`
  - `test_evaluate_computes_growing_trajectory`
  - `test_evaluate_sends_null_trajectory_when_no_previous_briefing`
  - `test_dispatch_sends_both_webhook_and_email_for_both_channel`
  - `test_dispatch_only_webhook_when_channel_is_webhook`
- Complexity: M

### Task 6.2 — Unit tests: AlertRule entity
- **File:** `tests/unit/test_alert_rule_entity.py` (create)
- Test `AlertRule.create(...)` produces correct defaults.
- Complexity: XS

### Task 6.3 — Integration tests: AlertRule API
- **File:** `tests/integration/test_alert_rules_api.py` (create)
- Use FastAPI `TestClient` + real SQLite (in-memory or file).
- Scenarios:
  - `test_create_alert_rule_returns_201`
  - `test_create_alert_rule_validates_threshold_out_of_range`
  - `test_create_alert_rule_validates_missing_webhook_url`
  - `test_list_alert_rules_filters_by_niche_id`
  - `test_delete_alert_rule_deactivates_it`
- Complexity: M

### Task 6.4 — Unit tests: WebhookNotificationAdapter
- **File:** `tests/unit/test_webhook_adapter.py` (create)
- Mock `httpx.AsyncClient` to simulate success, HTTP error, connection timeout.
- Scenarios:
  - `test_send_alert_to_returns_true_on_success`
  - `test_send_alert_to_returns_false_on_http_error`
  - `test_send_alert_to_returns_false_on_timeout`
- Complexity: S

---

## Implementation Order (recommended)

```
Phase 1 (all parallel) → Phase 2 (2.1+2.2 parallel, then 2.3) → Phase 3 (parallel)
→ Phase 4 (4.1 then 4.2) → Phase 5 (5.1 then 5.2) → Phase 6 (all parallel)
```

## Complexity Legend
- XS: < 30 lines, trivial
- S: 30–80 lines, straightforward
- M: 80–200 lines, requires careful design
- L: > 200 lines, split into sub-tasks if possible
