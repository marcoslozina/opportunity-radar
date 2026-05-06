# Proposal: Alert System

## Intent

Allow consumers (e.g., PropFlow, ESG verticals) to configure threshold-based alerts so they are proactively notified when high-scoring or trending opportunities appear in their niches — without polling the dashboard. Alerts are rule-driven: each rule defines a niche, a score threshold, and a delivery channel (webhook and/or email).

## Scope

- `AlertRule` domain entity with threshold, channel, and recipient configuration.
- `AlertRuleRepository` port + SQL implementation.
- `AlertEvaluationService` application service that evaluates rules post-pipeline.
- `WebhookNotificationAdapter` infrastructure adapter (HTTP POST).
- Extension of `NotificationPort` with `send_alert` method (backward-compatible).
- Extension of `ResendEmailAdapter` to implement `send_alert`.
- Hook point wired in the scheduler post-pipeline.
- CRUD API: `POST /alert-rules`, `GET /alert-rules`, `DELETE /alert-rules/{id}`.
- Duplicate suppression via `last_notified_at` on `AlertRule`.

## Out of Scope

- Push notifications (mobile/web).
- Alert history/audit log table (separate change).
- Complex subscription management (opt-in flows, email verification).
- Alert batching across niches (each rule fires independently).
- Retry queues for failed webhook deliveries (best-effort, logged).

---

## Options

### Option A — Inline in RunPipelineUseCase

**How it works:** `RunPipelineUseCase` receives `alert_rule_repo` and `notification_port` in its constructor. After `briefing_repo.save(briefing)`, it loads all active `AlertRule`s for the niche, evaluates thresholds, and calls `notification_port.send_alert` inline.

**Advantages:**
- Single call site — the use case already knows the `Briefing` and `Niche`.
- No additional orchestration layer needed.
- Fewer moving parts for a small team.

**Disadvantages:**
- Violates Single Responsibility: `RunPipelineUseCase` becomes responsible for both pipeline orchestration AND alert delivery.
- Constructor signature grows (already has 4 parameters; adding 2 more is noise).
- Harder to unit-test alert logic in isolation — you must stub the full pipeline context.
- Notification failure handling (`try/except`) mixed into pipeline control flow.
- Tightly couples alert evaluation to the pipeline lifecycle, making future changes (e.g., manual alert triggers, retroactive evaluation) harder.

**When to choose:** Prototypes, scripts, or when total complexity is very low.

---

### Option B — Dedicated AlertEvaluationService called by scheduler (RECOMMENDED)

**How it works:** A new `AlertEvaluationService` in `src/application/services/` encapsulates the evaluation logic. The scheduler's `_run_pipeline_for_niche` function calls `use_case.execute(niche_id)`, gets the returned `Briefing`, then calls `alert_service.evaluate(briefing, niche)` in a separate `try/except` block. The service queries active `AlertRule`s for the niche, evaluates thresholds and trajectory conditions, and dispatches notifications.

**Advantages:**
- `RunPipelineUseCase` stays focused: collect → score → synthesize → save → return. No notification concern.
- `AlertEvaluationService` is independently testable with fake `AlertRuleRepository` and fake `NotificationPort`.
- Notification failures are isolated — the scheduler wraps `evaluate()` in its own `try/except` that logs and continues.
- Future extensibility: the service can be triggered manually (e.g., `POST /alert-rules/{id}/test`), retroactively, or on a different schedule — without touching the pipeline.
- Clear separation of concerns aligns with the existing architecture: use cases orchestrate domain logic; services handle cross-cutting application concerns.
- Aligns with how `TrajectoryService` is structured: a reusable application service, not embedded in a use case.

**Disadvantages:**
- One more class and test file to maintain.
- The scheduler function `_run_pipeline_for_niche` grows slightly (one more async call after `execute`).

**When to choose:** Production systems, whenever testability and separation of concerns matter — which is always.

---

## Recommendation: Option B

Option B is the correct choice. `RunPipelineUseCase` already has four dependencies; adding two more to handle a cross-cutting concern (notifications) is a clear violation of Single Responsibility. `AlertEvaluationService` mirrors the existing `TrajectoryService` pattern in the codebase — a stateless application service that takes domain objects and coordinates infrastructure concerns. The scheduler's `_run_pipeline_for_niche` function is the natural orchestration point: it builds all dependencies inline, has full lifecycle control (try/except/finally), and already manages the async context.

---

## Success Criteria

- [ ] `AlertRule` can be created via `POST /alert-rules` with niche_id, threshold_score, delivery_channel, webhook_url, email.
- [ ] After each pipeline run, all active `AlertRule`s for the niche are evaluated.
- [ ] If any opportunity score `>= threshold_score`, a notification is dispatched.
- [ ] Webhook delivery: HTTP POST with JSON payload.
- [ ] Email delivery: via Resend using existing `resend_api_key`.
- [ ] Duplicate suppression: same alert rule does not fire within 1 hour of `last_notified_at`.
- [ ] Notification failure does NOT affect pipeline success status or return value.
- [ ] `GET /alert-rules?niche_id={id}` returns all rules for a niche.
- [ ] `DELETE /alert-rules/{id}` removes a rule.
