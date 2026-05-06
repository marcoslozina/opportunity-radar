# Exploration: Alert System

## Current State

### Notification Infrastructure
- `NotificationPort` ABC exists at `src/domain/ports/notification_port.py` with a single method:
  `async def send_briefing(self, briefing: Briefing, niche_name: str) -> bool`
- This port was designed for the `expansion-notifications` change (one-shot email after pipeline). It is implemented by `ResendEmailAdapter`.
- The port contract is coarse-grained: it receives an entire `Briefing` object, not a targeted alert payload. It must be extended (or a new port added) to support threshold-based delivery.

### Pipeline Execution Flow
1. **Scheduler** (`pipeline_scheduler.py`) uses APScheduler (AsyncIO) with a cron trigger from `settings.pipeline_schedule`.
2. `_run_pipeline_for_niche` builds `RunPipelineUseCase` inline and calls `execute(niche_id)`.
3. `RunPipelineUseCase.execute` collects signals → scores → synthesizes insights → saves `Briefing` → **returns the Briefing**. No post-run hook exists yet.
4. The scheduler discards the return value from `execute`; there is no post-processing step.
5. `RunPipelineUseCase` does NOT inject `NotificationPort` yet — that integration was scoped to `expansion-notifications` but not yet wired.

### Domain Entities
- `Opportunity`: `topic`, `score: OpportunityScore`, `recommended_action`, `domain_applicability`, `domain_reasoning`, `evidence`.
- `OpportunityScore`: five float sub-scores + `total: float` (0–100) + `confidence`.
- `ScoreTrajectory`: computed value object (`direction`: "GROWING ↑" / "COOLING ↓" / "STABLE →"). Available in API responses but NOT stored on the `Opportunity` entity itself — it is computed on-the-fly by `TrajectoryService` when serving the briefing.
- `Briefing`: `id`, `niche_id`, `opportunities`, `generated_at`. Has `.top_10` property.
- No `archetype` field exists anywhere in the domain yet.

### DB Models
- `NicheModel`, `BriefingModel`, `OpportunityModel`, `ApiKeyModel` — all use `String(36)` UUIDs as PKs.
- SQLAlchemy async with `DeclarativeBase`. Alembic manages migrations.
- No `AlertRuleModel` exists yet.

### Config
- `settings.resend_api_key` and `settings.notification_email` exist (added by expansion-notifications).
- No webhook or per-alert-rule configuration exists.

### Repository Ports
- `NicheRepository`, `OpportunityRepository`, `BriefingRepository`, `ApiKeyRepository` — all ABCs in `repository_ports.py`.
- No `AlertRuleRepository` exists yet.

### API
- FastAPI with routers per domain concept (`/briefings`, `/niches`, `/pipeline`, `/api-keys`).
- No `/alert-rules` route exists.

---

## Prior Art: expansion-notifications

The `expansion-notifications` change established the following patterns that `alert-system` MUST respect and build upon:

| Pattern | Decision |
|---------|----------|
| `NotificationPort` ABC | Coarse method `send_briefing(briefing, niche_name)`. Needs extension for alert payloads. |
| `ResendEmailAdapter` | Concrete implementation; `alert-system` adds `WebhookNotificationAdapter` alongside it. |
| Failure tolerance | Notification failure must NOT fail pipeline. Already established as an NFR. |
| Config via pydantic-settings | `resend_api_key` and `notification_email` already in `Settings`. |
| Integration point | `RunPipelineUseCase.execute` end — post-briefing-save. |

Key delta: `expansion-notifications` used a static single recipient. `alert-system` introduces **dynamic per-rule recipients** (each `AlertRule` has its own `webhook_url` or `email`), requiring the port to accept target metadata rather than using global config.

---

## Key Questions

1. **NotificationPort signature**: Should we extend `send_briefing` or add a new `send_alert` method? Given that alert payloads are structurally different from briefing summaries (targeted top opportunity, threshold context), a new `send_alert(payload: AlertPayload, channel: DeliveryChannel)` method is cleaner.

2. **Trajectory in alert payload**: `ScoreTrajectory` is not stored on `Opportunity` — it's computed by `TrajectoryService` at read time. For the alert payload "GROWING ↑" filter, we need to either: (a) compute trajectory inside `AlertEvaluationService` using `BriefingRepository.get_previous`, or (b) accept that trajectory is only available if a previous briefing exists.

3. **Archetype field**: The spec mentions `archetype` in the notification payload. No such field exists in the domain. This likely refers to `domain_applicability` (e.g., "propflow", "esg") or is a new field to add to `Opportunity`. Recommend mapping `domain_applicability` as the archetype substitute until explicitly required otherwise.

4. **Duplicate suppression scope**: "Same niche within 1 hour" — this is per-rule, not global. An `AlertRule` with `last_notified_at` satisfies this without a separate notification log table.

5. **Score normalization**: `OpportunityScore.total` is 0–100. The threshold in the spec is `>= 8.5`. This likely means the normalized 0–10 scale. Clarification needed: is the threshold applied to `total` (0–100 scale) or a normalized version? Recommend using `total` directly and documenting the 0–100 scale in the API.

---

## Technical Findings

- **Hook point**: The scheduler calls `_run_pipeline_for_niche` which builds `RunPipelineUseCase` inline. The cleanest hook is injecting `AlertEvaluationService` into `RunPipelineUseCase` (or having the scheduler call it post-`execute`). The dedicated service option (Option B) avoids polluting the use case.
- **Existing `scoring_engine` discrepancy**: The scheduler passes `scoring_engine=ScoringEngine()` to `RunPipelineUseCase`, but `RunPipelineUseCase.__init__` does NOT have a `scoring_engine` parameter — it uses `ScoringFactory` internally. This is a pre-existing inconsistency and does not block alert-system.
- **AsyncSessionFactory**: The scheduler creates a session per niche run. `AlertEvaluationService` will need its own session or be called within the same context.
- **APScheduler**: Already async-native; calling `AlertEvaluationService` after `execute` within `_run_pipeline_for_niche` is straightforward.

---

## Hypothesis

The alert system should be implemented as a **dedicated `AlertEvaluationService`** (Option B) that is called by the scheduler immediately after a successful `RunPipelineUseCase.execute`. This keeps `RunPipelineUseCase` single-responsibility, makes the evaluation independently testable, and allows the service to accept `Briefing + niche` data without coupling the core pipeline to notification concerns.

The `NotificationPort` should be extended with a `send_alert` method accepting an `AlertPayload` dataclass, keeping backward compatibility with `send_briefing`. Both `WebhookNotificationAdapter` and `ResendEmailAdapter` implement both methods.
