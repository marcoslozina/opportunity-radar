# Technical Design: Alert System

## Architecture Overview

Following the Clean/Hexagonal Architecture already established in the project:

```
API Route (POST/GET/DELETE /alert-rules)
    ↓
Application: AlertEvaluationService  ←  Scheduler hook
    ↓                ↓
Domain Ports:   AlertRuleRepository (ABC)
                NotificationPort (ABC — extended)
    ↓                ↓
Infrastructure: SqlAlertRuleRepository   WebhookNotificationAdapter
                                         ResendEmailAdapter (extended)
```

Dependency rule: Domain knows nothing about infrastructure. `AlertEvaluationService` depends only on ports (ABCs).

---

## 1. Domain Layer

### 1.1 AlertRule Entity

**File:** `src/domain/entities/alert_rule.py`

```python
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4


@dataclass(frozen=True)
class AlertRuleId:
    value: UUID

    def __str__(self) -> str:
        return str(self.value)


@dataclass
class AlertRule:
    id: AlertRuleId
    niche_id: str                      # UUID as str — consistent with existing pattern
    threshold_score: float             # 0.0–100.0; fires when any opportunity >= this
    delivery_channel: str              # "webhook" | "email" | "both"
    webhook_url: str | None
    email: str | None
    active: bool = field(default=True)
    last_notified_at: datetime | None = field(default=None)
    created_at: datetime = field(default_factory=datetime.utcnow)

    @classmethod
    def create(
        cls,
        niche_id: str,
        threshold_score: float,
        delivery_channel: str,
        webhook_url: str | None = None,
        email: str | None = None,
    ) -> AlertRule:
        return cls(
            id=AlertRuleId(uuid4()),
            niche_id=niche_id,
            threshold_score=threshold_score,
            delivery_channel=delivery_channel,
            webhook_url=webhook_url,
            email=email,
        )
```

**Notes:**
- `niche_id` stored as `str` (UUID string) for consistency with `OpportunityModel`, `BriefingModel`, etc.
- `delivery_channel` is a plain `str` with validation at the API/application layer. Using a `Literal` type or `Enum` is a clean alternative — but keep the domain entity free of Pydantic.
- `last_notified_at` is mutable (the entity is not frozen) because it is updated after each notification.

### 1.2 AlertPayload Value Object

**File:** `src/domain/value_objects/alert_payload.py`

```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class AlertPayload:
    alert_rule_id: str
    niche_id: str
    niche_name: str
    triggered_at: datetime
    threshold_score: float
    top_opportunity_topic: str
    top_opportunity_score: float
    top_opportunity_trajectory: str | None   # "GROWING ↑" | "COOLING ↓" | "STABLE →" | None
    top_opportunity_domain_applicability: str
    top_opportunity_recommended_action: str
```

This value object is the canonical contract between `AlertEvaluationService` and both notification adapters. It is domain-pure (no external deps).

### 1.3 NotificationPort — Extended

**File:** `src/domain/ports/notification_port.py`

Add `send_alert` while preserving `send_briefing` for backward compatibility:

```python
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from domain.entities.briefing import Briefing
    from domain.value_objects.alert_payload import AlertPayload


class NotificationPort(ABC):
    @abstractmethod
    async def send_briefing(self, briefing: Briefing, niche_name: str) -> bool:
        """Send a full briefing summary. Used by expansion-notifications."""
        ...

    @abstractmethod
    async def send_alert(self, payload: AlertPayload) -> bool:
        """Send a targeted threshold alert. Used by alert-system."""
        ...
```

**Note:** `ResendEmailAdapter` already implements `send_briefing`. It must now also implement `send_alert`. `WebhookNotificationAdapter` implements both (though `send_briefing` can raise `NotImplementedError` or log a no-op if webhooks are not used for briefing delivery).

### 1.4 AlertRuleRepository Port

**File:** `src/domain/ports/repository_ports.py` — append to existing file

```python
from domain.entities.alert_rule import AlertRule, AlertRuleId

class AlertRuleRepository(ABC):
    @abstractmethod
    async def save(self, rule: AlertRule) -> None: ...

    @abstractmethod
    async def find_by_id(self, rule_id: AlertRuleId) -> AlertRule | None: ...

    @abstractmethod
    async def find_active_by_niche(self, niche_id: str) -> list[AlertRule]: ...

    @abstractmethod
    async def deactivate(self, rule_id: AlertRuleId) -> None: ...

    @abstractmethod
    async def list_all(self, niche_id: str | None = None) -> list[AlertRule]: ...
```

---

## 2. Infrastructure Layer

### 2.1 AlertRuleModel (DB)

**File:** `src/infrastructure/db/models.py` — append to existing file

```python
class AlertRuleModel(Base):
    __tablename__ = "alert_rules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    niche_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("niches.id", ondelete="CASCADE"), nullable=False
    )
    threshold_score: Mapped[float] = mapped_column(Float, nullable=False)
    delivery_channel: Mapped[str] = mapped_column(String(10), nullable=False)  # webhook|email|both
    webhook_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_notified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_alert_rules_niche_id_active", "niche_id", "active"),
    )
```

**Index rationale:** `find_active_by_niche(niche_id)` is the hot path — called after every pipeline run. Composite index on `(niche_id, active)` covers the query efficiently.

### 2.2 Alembic Migration

**File:** `alembic/versions/{hash}_add_alert_rules_table.py`

```python
def upgrade() -> None:
    op.create_table(
        "alert_rules",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("niche_id", sa.String(36), sa.ForeignKey("niches.id", ondelete="CASCADE"), nullable=False),
        sa.Column("threshold_score", sa.Float(), nullable=False),
        sa.Column("delivery_channel", sa.String(10), nullable=False),
        sa.Column("webhook_url", sa.String(2048), nullable=True),
        sa.Column("email", sa.String(320), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("last_notified_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_alert_rules_niche_id_active", "alert_rules", ["niche_id", "active"])


def downgrade() -> None:
    op.drop_index("ix_alert_rules_niche_id_active", table_name="alert_rules")
    op.drop_table("alert_rules")
```

### 2.3 SqlAlertRuleRepository

**File:** `src/infrastructure/db/repositories.py` — append to existing file

```python
class SqlAlertRuleRepository(AlertRuleRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, rule: AlertRule) -> None:
        model = self._to_model(rule)
        await self._session.merge(model)
        await self._session.flush()

    async def find_by_id(self, rule_id: AlertRuleId) -> AlertRule | None:
        result = await self._session.get(AlertRuleModel, str(rule_id))
        return self._to_entity(result) if result else None

    async def find_active_by_niche(self, niche_id: str) -> list[AlertRule]:
        stmt = select(AlertRuleModel).where(
            AlertRuleModel.niche_id == niche_id,
            AlertRuleModel.active.is_(True),
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def deactivate(self, rule_id: AlertRuleId) -> None:
        stmt = (
            update(AlertRuleModel)
            .where(AlertRuleModel.id == str(rule_id))
            .values(active=False)
        )
        await self._session.execute(stmt)
        await self._session.flush()

    async def list_all(self, niche_id: str | None = None) -> list[AlertRule]:
        stmt = select(AlertRuleModel)
        if niche_id:
            stmt = stmt.where(AlertRuleModel.niche_id == niche_id)
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]
```

### 2.4 WebhookNotificationAdapter

**File:** `src/infrastructure/adapters/webhook_notification.py` (new file)

```python
from __future__ import annotations

import logging
import httpx
from dataclasses import asdict
from datetime import datetime

from domain.ports.notification_port import NotificationPort
from domain.value_objects.alert_payload import AlertPayload

logger = logging.getLogger(__name__)

WEBHOOK_TIMEOUT_SECONDS = 10


class WebhookNotificationAdapter(NotificationPort):
    async def send_briefing(self, briefing, niche_name: str) -> bool:
        # Webhook channel is not used for briefing delivery — no-op
        logger.debug("WebhookNotificationAdapter.send_briefing is a no-op")
        return False

    async def send_alert(self, payload: AlertPayload) -> bool:
        if not payload:
            return False
        # webhook_url is resolved by AlertEvaluationService before calling this
        # The adapter receives the target URL via the payload's alert_rule context
        # In practice, AlertEvaluationService passes the URL separately or via AlertPayload extension
        # See AlertEvaluationService for the dispatch pattern
        raise NotImplementedError(
            "Use send_alert_to(payload, webhook_url) instead — see AlertEvaluationService"
        )

    async def send_alert_to(self, payload: AlertPayload, webhook_url: str) -> bool:
        body = {
            "alert_rule_id": payload.alert_rule_id,
            "niche_id": payload.niche_id,
            "niche_name": payload.niche_name,
            "triggered_at": payload.triggered_at.isoformat(),
            "threshold_score": payload.threshold_score,
            "top_opportunity": {
                "topic": payload.top_opportunity_topic,
                "score_total": payload.top_opportunity_score,
                "trajectory_direction": payload.top_opportunity_trajectory,
                "domain_applicability": payload.top_opportunity_domain_applicability,
                "recommended_action": payload.top_opportunity_recommended_action,
            },
        }
        try:
            async with httpx.AsyncClient(timeout=WEBHOOK_TIMEOUT_SECONDS) as client:
                response = await client.post(webhook_url, json=body)
                response.raise_for_status()
                logger.info("Webhook delivered: rule=%s status=%d", payload.alert_rule_id, response.status_code)
                return True
        except Exception as exc:
            logger.error("Webhook delivery failed: rule=%s url=%s error=%s", payload.alert_rule_id, webhook_url, exc)
            return False
```

**Design note:** `send_alert_to(payload, webhook_url)` is a concrete method that `AlertEvaluationService` calls directly (since `AlertEvaluationService` knows the concrete adapter type when dispatching webhooks). This avoids encoding the URL inside `AlertPayload` (which would be strange — the payload describes what happened, not where to send it).

### 2.5 ResendEmailAdapter — Extended

**File:** `src/infrastructure/adapters/resend_email.py` — extend existing class

Add `send_alert` implementation that:
1. Accepts `AlertPayload`.
2. Sends to `payload.alert_rule.email` (passed via a new concrete method `send_alert_to_email(payload, email)`), NOT `settings.notification_email`.
3. Uses an HTML template focused on the single top opportunity.

```python
async def send_alert_to_email(self, payload: AlertPayload, email: str) -> bool:
    subject = f"[Opportunity Radar] Alert: {payload.niche_name} — score {payload.top_opportunity_score}"
    html_body = self._render_alert_html(payload)
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={"from": "radar@resend.dev", "to": [email], "subject": subject, "html": html_body},
            )
            response.raise_for_status()
            return True
    except Exception as exc:
        logger.error("Alert email failed: rule=%s error=%s", payload.alert_rule_id, exc)
        return False
```

---

## 3. Application Layer

### 3.1 AlertEvaluationService

**File:** `src/application/services/alert_evaluation_service.py` (new file)

```python
from __future__ import annotations

import logging
from datetime import datetime, timedelta

from domain.entities.alert_rule import AlertRule
from domain.entities.briefing import Briefing
from domain.entities.niche import Niche
from domain.ports.repository_ports import AlertRuleRepository, BriefingRepository
from domain.value_objects.alert_payload import AlertPayload
from domain.value_objects.score_trajectory import ScoreTrajectory
from infrastructure.adapters.webhook_notification import WebhookNotificationAdapter
from infrastructure.adapters.resend_email import ResendEmailAdapter

logger = logging.getLogger(__name__)

SUPPRESSION_WINDOW_MINUTES = 60


class AlertEvaluationService:
    def __init__(
        self,
        alert_rule_repo: AlertRuleRepository,
        briefing_repo: BriefingRepository,
        webhook_adapter: WebhookNotificationAdapter,
        email_adapter: ResendEmailAdapter,
    ) -> None:
        self._alert_rule_repo = alert_rule_repo
        self._briefing_repo = briefing_repo
        self._webhook_adapter = webhook_adapter
        self._email_adapter = email_adapter

    async def evaluate(self, briefing: Briefing, niche: Niche) -> None:
        rules = await self._alert_rule_repo.find_active_by_niche(str(niche.id))
        if not rules:
            return

        previous_briefing = await self._briefing_repo.get_previous(niche.id)
        top_opp = max(briefing.opportunities, key=lambda o: o.score.total, default=None)
        if top_opp is None:
            return

        trajectory = self._compute_trajectory(top_opp.topic, briefing, previous_briefing)

        for rule in rules:
            try:
                await self._evaluate_rule(rule, briefing, niche, top_opp, trajectory)
            except Exception as exc:
                logger.error("Alert evaluation failed: rule=%s error=%s", rule.id, exc)

    async def _evaluate_rule(self, rule, briefing, niche, top_opp, trajectory) -> None:
        # Check threshold
        qualifying = [o for o in briefing.opportunities if o.score.total >= rule.threshold_score]
        if not qualifying:
            return

        # Duplicate suppression
        if rule.last_notified_at is not None:
            elapsed = datetime.utcnow() - rule.last_notified_at
            if elapsed < timedelta(minutes=SUPPRESSION_WINDOW_MINUTES):
                logger.info("Alert suppressed (cooldown): rule=%s", rule.id)
                return

        best = max(qualifying, key=lambda o: o.score.total)
        payload = AlertPayload(
            alert_rule_id=str(rule.id),
            niche_id=str(niche.id),
            niche_name=niche.name,
            triggered_at=datetime.utcnow(),
            threshold_score=rule.threshold_score,
            top_opportunity_topic=best.topic,
            top_opportunity_score=best.score.total,
            top_opportunity_trajectory=trajectory.direction if trajectory else None,
            top_opportunity_domain_applicability=best.domain_applicability,
            top_opportunity_recommended_action=best.recommended_action,
        )

        dispatched = await self._dispatch(rule, payload)
        if dispatched:
            rule.last_notified_at = datetime.utcnow()
            await self._alert_rule_repo.save(rule)

    async def _dispatch(self, rule: AlertRule, payload: AlertPayload) -> bool:
        webhook_ok = True
        email_ok = True

        if rule.delivery_channel in ("webhook", "both") and rule.webhook_url:
            webhook_ok = await self._webhook_adapter.send_alert_to(payload, rule.webhook_url)

        if rule.delivery_channel in ("email", "both") and rule.email:
            email_ok = await self._email_adapter.send_alert_to_email(payload, rule.email)

        return webhook_ok or email_ok

    def _compute_trajectory(self, topic: str, current: Briefing, previous: Briefing | None) -> ScoreTrajectory | None:
        if previous is None:
            return None
        current_opp = next((o for o in current.opportunities if o.topic == topic), None)
        prev_opp = next((o for o in previous.opportunities if o.topic == topic), None)
        if current_opp is None or prev_opp is None:
            return None
        return ScoreTrajectory.compute(
            current_total=current_opp.score.total,
            previous_total=prev_opp.score.total,
            compared_at=previous.generated_at,
        )
```

**Design decisions:**
- `AlertEvaluationService` takes CONCRETE adapter types (`WebhookNotificationAdapter`, `ResendEmailAdapter`) rather than a single `NotificationPort`. This is because the dispatch logic branches on `delivery_channel` and must call different concrete methods (`send_alert_to` vs `send_alert_to_email`) with different signatures. If both adapters are unified under a single port, the port must expose both methods or accept routing metadata — which muddies the abstraction. The trade-off: slightly tighter coupling to infrastructure, gained testability by injecting fakes of each adapter.
- Alternatively, a `MultiChannelNotificationPort` wrapper could be used — but that is over-engineering for two channels.

### 3.2 Hook in Scheduler

**File:** `src/infrastructure/scheduler/pipeline_scheduler.py` — update `_run_pipeline_for_niche`

After `await use_case.execute(NicheId(...))`, add:

```python
# Post-pipeline: evaluate alert rules (best-effort — must not propagate exceptions)
try:
    from application.services.alert_evaluation_service import AlertEvaluationService
    from infrastructure.adapters.webhook_notification import WebhookNotificationAdapter
    from infrastructure.adapters.resend_email import ResendEmailAdapter
    from infrastructure.db.repositories import SqlAlertRuleRepository

    niche = await SQLNicheRepository(session).find_by_id(NicheId(UUID(niche_id_str)))
    if niche and briefing:
        alert_service = AlertEvaluationService(
            alert_rule_repo=SqlAlertRuleRepository(session),
            briefing_repo=SQLBriefingRepository(session),
            webhook_adapter=WebhookNotificationAdapter(),
            email_adapter=ResendEmailAdapter(settings.resend_api_key),
        )
        await alert_service.evaluate(briefing, niche)
except Exception as exc:
    logger.error("Alert evaluation error (non-fatal): niche_id=%s error=%s", niche_id_str, exc)
```

**Note:** `use_case.execute` already returns `briefing`. Capture that return value.

---

## 4. API Layer

### 4.1 Pydantic Schemas

**File:** `src/api/schemas/alert_rule.py` (new file)

```python
from __future__ import annotations
from datetime import datetime
from pydantic import BaseModel, field_validator
from typing import Literal


class CreateAlertRuleRequest(BaseModel):
    niche_id: str
    threshold_score: float
    delivery_channel: Literal["webhook", "email", "both"]
    webhook_url: str | None = None
    email: str | None = None

    @field_validator("threshold_score")
    @classmethod
    def validate_threshold(cls, v: float) -> float:
        if not 0.0 <= v <= 100.0:
            raise ValueError("threshold_score must be between 0.0 and 100.0")
        return v

    @field_validator("webhook_url")
    @classmethod
    def validate_webhook_url(cls, v: str | None, info) -> str | None:
        channel = info.data.get("delivery_channel")
        if channel in ("webhook", "both") and not v:
            raise ValueError("webhook_url is required when delivery_channel is 'webhook' or 'both'")
        return v

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str | None, info) -> str | None:
        channel = info.data.get("delivery_channel")
        if channel in ("email", "both") and not v:
            raise ValueError("email is required when delivery_channel is 'email' or 'both'")
        return v


class AlertRuleResponse(BaseModel):
    id: str
    niche_id: str
    threshold_score: float
    delivery_channel: str
    webhook_url: str | None
    email: str | None
    active: bool
    last_notified_at: datetime | None
    created_at: datetime
```

### 4.2 Router

**File:** `src/api/routes/alert_rules.py` (new file)

```
POST   /alert-rules              → create_alert_rule    → 201 AlertRuleResponse
GET    /alert-rules?niche_id=    → list_alert_rules     → 200 list[AlertRuleResponse]
DELETE /alert-rules/{id}         → delete_alert_rule    → 204 No Content
```

**Auth:** Protected by existing API key middleware (same as other routes).

**Dependency injection:** Router injects `SqlAlertRuleRepository` via FastAPI `Depends` + `get_session`.

---

## 5. Dependency Wiring Summary

```
FastAPI App
└── /alert-rules router
    └── SqlAlertRuleRepository(session)

APScheduler
└── _run_pipeline_for_niche(niche_id_str)
    ├── RunPipelineUseCase.execute() → Briefing
    └── AlertEvaluationService.evaluate(briefing, niche)
        ├── SqlAlertRuleRepository(session)
        ├── SQLBriefingRepository(session)       ← for trajectory computation
        ├── WebhookNotificationAdapter()
        └── ResendEmailAdapter(resend_api_key)
```

---

## 6. Files to Create / Modify

| Action | File |
|--------|------|
| CREATE | `src/domain/entities/alert_rule.py` |
| CREATE | `src/domain/value_objects/alert_payload.py` |
| MODIFY | `src/domain/ports/notification_port.py` — add `send_alert` abstract method |
| MODIFY | `src/domain/ports/repository_ports.py` — add `AlertRuleRepository` ABC |
| MODIFY | `src/infrastructure/db/models.py` — add `AlertRuleModel` |
| CREATE | `alembic/versions/{hash}_add_alert_rules_table.py` |
| MODIFY | `src/infrastructure/db/repositories.py` — add `SqlAlertRuleRepository` |
| CREATE | `src/infrastructure/adapters/webhook_notification.py` |
| MODIFY | `src/infrastructure/adapters/resend_email.py` — add `send_alert` / `send_alert_to_email` |
| CREATE | `src/application/services/alert_evaluation_service.py` |
| MODIFY | `src/infrastructure/scheduler/pipeline_scheduler.py` — hook post-execute |
| CREATE | `src/api/schemas/alert_rule.py` |
| CREATE | `src/api/routes/alert_rules.py` |
| MODIFY | `src/api/main.py` (or app factory) — register `/alert-rules` router |
| CREATE | `tests/unit/test_alert_evaluation_service.py` |
| CREATE | `tests/integration/test_alert_rules_api.py` |
