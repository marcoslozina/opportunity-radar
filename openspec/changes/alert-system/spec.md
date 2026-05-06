# Specification: Alert System

## User Stories

### Story: Configure a threshold alert
- **AS** a vertical consumer (e.g., PropFlow operator)
- **I WANT** to register an alert rule for a niche with a score threshold and delivery channel
- **SO THAT** I am automatically notified when high-scoring opportunities appear without polling the dashboard.

### Story: Receive a webhook alert
- **AS** a PropFlow backend service
- **I WANT** to receive an HTTP POST to my webhook URL when a trigger condition is met
- **SO THAT** I can act on the opportunity programmatically (e.g., update a feed, trigger a workflow).

### Story: Receive an email alert
- **AS** an ESG consultant
- **I WANT** to receive an email when a GROWING opportunity appears in my niche
- **SO THAT** I can review the finding before the next board meeting.

### Story: Avoid notification spam
- **AS** a consumer with active alert rules
- **I WANT** not to receive duplicate notifications for the same rule within a short window
- **SO THAT** I am not spammed when a pipeline runs multiple times in quick succession.

---

## Functional Requirements

### FR-01: AlertRule Entity
An `AlertRule` MUST have the following fields:
- `id`: UUID (generated)
- `niche_id`: UUID — references an existing `Niche`
- `threshold_score`: float — score on the 0–100 scale (`OpportunityScore.total`); alert fires when any opportunity total `>= threshold_score`
- `delivery_channel`: enum — one of `webhook`, `email`, `both`
- `webhook_url`: str | None — required when `delivery_channel` is `webhook` or `both`; must be a valid HTTP/HTTPS URL
- `email`: str | None — required when `delivery_channel` is `email` or `both`
- `active`: bool — default True; inactive rules are never evaluated
- `last_notified_at`: datetime | None — updated on each successful dispatch; used for duplicate suppression
- `created_at`: datetime — set on creation

### FR-02: AlertRule Validation
- If `delivery_channel` is `webhook` or `both`, `webhook_url` MUST be present and non-empty.
- If `delivery_channel` is `email` or `both`, `email` MUST be present and non-empty.
- `threshold_score` MUST be in range [0.0, 100.0].
- `niche_id` MUST reference an existing niche (validated at creation time via API).

### FR-03: Post-Pipeline Evaluation
After each successful `RunPipelineUseCase.execute` call, the system MUST evaluate all active `AlertRule`s whose `niche_id` matches the pipeline's niche.

### FR-04: Threshold Trigger
An `AlertRule` fires if ANY opportunity in the resulting `Briefing` has `score.total >= alert_rule.threshold_score`.

### FR-05: Notification Payload
When an alert fires, the notification MUST include:
- `niche_name`: str — human-readable niche name
- `niche_id`: str — UUID string
- `triggered_at`: ISO 8601 datetime string
- `threshold_score`: float — the rule's threshold
- `top_opportunity`: object containing:
  - `topic`: str
  - `score_total`: float
  - `trajectory_direction`: str | None — "GROWING ↑", "COOLING ↓", "STABLE →", or null if no previous briefing exists
  - `domain_applicability`: str — maps to the domain archetype (e.g., "propflow", "esg")
  - `recommended_action`: str
- `alert_rule_id`: str — UUID of the rule that fired

The `top_opportunity` is the single highest-scoring opportunity that meets or exceeds the threshold.

### FR-06: Webhook Delivery
When `delivery_channel` is `webhook` or `both`, the system MUST send an HTTP POST request to `webhook_url` with:
- Content-Type: `application/json`
- Body: the notification payload serialized as JSON
- Timeout: 10 seconds
- No retries (best-effort)

### FR-07: Email Delivery
When `delivery_channel` is `email` or `both`, the system MUST send an email via Resend using `settings.resend_api_key`:
- To: the `email` field of the `AlertRule` (NOT the global `settings.notification_email`)
- Subject: `[Opportunity Radar] Alert: {niche_name} — score {score_total}`
- Body: HTML email with the notification payload rendered as a structured summary

### FR-08: AlertRule CRUD API
The system MUST expose the following endpoints:
- `POST /alert-rules` — create a new `AlertRule`; returns 201 with the created rule
- `GET /alert-rules` — list all alert rules; supports optional query param `?niche_id={uuid}` to filter
- `DELETE /alert-rules/{id}` — deactivate (soft-delete: set `active = False`) an alert rule; returns 204

### FR-09: Duplicate Suppression
An `AlertRule` MUST NOT fire again if its `last_notified_at` is within the last 60 minutes at the time of evaluation. After a successful dispatch, `last_notified_at` is updated to `datetime.utcnow()`.

### FR-10: Update last_notified_at
After a successful notification dispatch (webhook or email), `last_notified_at` on the `AlertRule` MUST be persisted via `AlertRuleRepository.save`.

---

## Non-Functional Requirements

### NFR-01: Pipeline Isolation
Notification failure (network error, Resend API error, invalid webhook URL) MUST NOT fail the pipeline run. The error MUST be logged at ERROR level and execution continues.

### NFR-02: Evaluation Performance
`AlertEvaluationService.evaluate` MUST complete within 30 seconds regardless of the number of active rules. Webhook calls are made sequentially per rule (no parallel fan-out required at this scale).

### NFR-03: No Duplicate Suppression Across Rules
Duplicate suppression is per-rule, not per-niche. Two different `AlertRule`s for the same niche can both fire in the same pipeline run if neither has been notified within the last hour.

---

## Acceptance Scenarios

### Scenario 1: Alert fires for high-score opportunity
```
GIVEN an active AlertRule for niche "real_estate" with threshold_score=75.0 and delivery_channel="webhook"
AND last_notified_at is None
WHEN the pipeline runs and produces a Briefing where the top opportunity has score.total=82.5
THEN the webhook is called with a JSON payload containing topic, score_total=82.5, niche_name="real_estate"
AND last_notified_at is updated to now
```

### Scenario 2: Alert does not fire when all scores are below threshold
```
GIVEN an active AlertRule with threshold_score=90.0
WHEN the pipeline produces a Briefing where the highest score.total=85.0
THEN no notification is sent
AND last_notified_at is not updated
```

### Scenario 3: Duplicate suppression prevents re-notification
```
GIVEN an active AlertRule with threshold_score=70.0
AND last_notified_at was set 30 minutes ago
WHEN the pipeline produces a Briefing with top score=88.0
THEN no notification is sent (suppressed)
AND last_notified_at is not updated
```

### Scenario 4: Duplicate suppression window expired
```
GIVEN an active AlertRule with threshold_score=70.0
AND last_notified_at was set 90 minutes ago
WHEN the pipeline produces a Briefing with top score=88.0
THEN the notification IS sent
AND last_notified_at is updated to now
```

### Scenario 5: Webhook failure does not break pipeline
```
GIVEN an active AlertRule with delivery_channel="webhook" and an invalid webhook_url
WHEN the pipeline runs and the alert condition is met
THEN the HTTP POST fails with a connection error
AND the pipeline is still marked as completed successfully
AND the error is logged at ERROR level
```

### Scenario 6: Both channel sends webhook and email
```
GIVEN an active AlertRule with delivery_channel="both", a valid webhook_url, and a valid email
WHEN the alert condition is met
THEN both the webhook POST and the Resend email are attempted independently
AND failure of one does not prevent the other from being attempted
```

### Scenario 7: Inactive rule is never evaluated
```
GIVEN an AlertRule with active=False
WHEN the pipeline runs for the rule's niche
THEN the rule is not loaded or evaluated
```

### Scenario 8: AlertRule created via API
```
GIVEN a POST /alert-rules with valid body: niche_id, threshold_score=80.0, delivery_channel="email", email="user@example.com"
THEN 201 is returned with the created AlertRule including its generated id
```

### Scenario 9: Alert with GROWING trajectory in payload
```
GIVEN a niche with two consecutive pipeline runs
AND the top opportunity's score increased by more than 5%
WHEN the alert fires
THEN trajectory_direction in the payload is "GROWING ↑"
```

### Scenario 10: Alert fires with no previous briefing (no trajectory)
```
GIVEN an AlertRule for a niche that has only one briefing (first run)
WHEN the alert condition is met
THEN the notification is sent with trajectory_direction=null
```
