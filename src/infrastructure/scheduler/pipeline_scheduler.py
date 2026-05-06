from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from config import settings

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

_running: set[str] = set()


async def _run_pipeline_for_niche(niche_id_str: str) -> None:
    if niche_id_str in _running:
        logger.warning("PIPELINE_ALREADY_RUNNING niche_id=%s", niche_id_str)
        return

    _running.add(niche_id_str)
    try:
        from infrastructure.db.session import AsyncSessionFactory
        from infrastructure.db.repositories import SQLNicheRepository, SQLBriefingRepository
        from infrastructure.adapters.hacker_news import HackerNewsAdapter
        from infrastructure.adapters.reddit import RedditAdapter
        from infrastructure.adapters.google_trends import GoogleTrendsAdapter
        from infrastructure.adapters.youtube import YouTubeAdapter
        from infrastructure.adapters.product_hunt import ProductHuntAdapter
        from infrastructure.adapters.serp import SerpAdapter
        from infrastructure.adapters.claude_insight import ClaudeInsightAdapter
        from application.services.scoring_engine import ScoringEngine
        from application.use_cases.run_pipeline import RunPipelineUseCase
        from domain.entities.niche import NicheId
        from uuid import UUID

        async with AsyncSessionFactory() as session:
            use_case = RunPipelineUseCase(
                niche_repo=SQLNicheRepository(session),
                briefing_repo=SQLBriefingRepository(session),
                collectors=[
                    HackerNewsAdapter(),
                    RedditAdapter(),
                    GoogleTrendsAdapter(),
                    YouTubeAdapter(),
                    ProductHuntAdapter(),
                    SerpAdapter(),
                ],
                insight_port=ClaudeInsightAdapter(),
                scoring_engine=ScoringEngine(),
            )
            briefing = await use_case.execute(NicheId(UUID(niche_id_str)))
            logger.info("Pipeline completed for niche_id=%s", niche_id_str)

        # Post-pipeline: evaluate alert rules (best-effort — must not propagate exceptions)
        try:
            from infrastructure.db.session import AsyncSessionFactory as _Factory
            from infrastructure.db.repositories import SQLNicheRepository as _NicheRepo, SQLBriefingRepository as _BriefingRepo, SqlAlertRuleRepository
            from infrastructure.adapters.webhook_notification import WebhookNotificationAdapter
            from infrastructure.adapters.resend_email import ResendEmailAdapter
            from application.services.alert_evaluation_service import AlertEvaluationService
            from domain.entities.niche import NicheId as _NicheId
            from uuid import UUID as _UUID

            async with _Factory() as alert_session:
                niche_repo = _NicheRepo(alert_session)
                niche = await niche_repo.find_by_id(_NicheId(_UUID(niche_id_str)))
                if niche and briefing:
                    alert_service = AlertEvaluationService(
                        alert_rule_repo=SqlAlertRuleRepository(alert_session),
                        briefing_repo=_BriefingRepo(alert_session),
                        webhook_adapter=WebhookNotificationAdapter(),
                        email_adapter=ResendEmailAdapter(settings.resend_api_key),
                    )
                    await alert_service.evaluate(briefing, niche)
        except Exception as exc:
            logger.error("Alert evaluation error (non-fatal): niche_id=%s error=%s", niche_id_str, exc)
    except Exception as exc:
        logger.error("Pipeline failed for niche_id=%s: %s", niche_id_str, exc)
    finally:
        _running.discard(niche_id_str)


async def _run_product_pipeline_for_niche(niche_id_str: str) -> None:
    if niche_id_str in _running:
        logger.warning("PRODUCT_PIPELINE_ALREADY_RUNNING niche_id=%s", niche_id_str)
        return

    _running.add(niche_id_str)
    try:
        from infrastructure.db.session import AsyncSessionFactory
        from infrastructure.db.repositories import SQLNicheRepository
        from infrastructure.db.product_repositories import SQLProductBriefingRepository
        from infrastructure.adapters.frustration_signal import FrustrationSignalAdapter
        from infrastructure.adapters.serp_product import SerpProductAdapter
        from infrastructure.adapters.claude_product_discovery import ClaudeProductDiscoveryAdapter
        from application.services.profitability_scoring_engine import ProfitabilityScoringEngine
        from application.use_cases.run_product_discovery import RunProductDiscoveryUseCase
        from domain.entities.niche import NicheId
        from uuid import UUID

        async with AsyncSessionFactory() as session:
            use_case = RunProductDiscoveryUseCase(
                niche_repo=SQLNicheRepository(session),
                product_briefing_repo=SQLProductBriefingRepository(session),
                collectors=[
                    FrustrationSignalAdapter(),
                    SerpProductAdapter(),
                ],
                discovery_port=ClaudeProductDiscoveryAdapter(),
                scoring_engine=ProfitabilityScoringEngine(),
            )
            await use_case.execute(NicheId(UUID(niche_id_str)))
            logger.info("Product pipeline completed for niche_id=%s", niche_id_str)
    except Exception as exc:
        logger.error("Product pipeline failed for niche_id=%s: %s", niche_id_str, exc)
    finally:
        _running.discard(niche_id_str)


async def schedule_all_niches() -> None:
    from infrastructure.db.session import AsyncSessionFactory
    from infrastructure.db.repositories import SQLNicheRepository

    async with AsyncSessionFactory() as session:
        niches = await SQLNicheRepository(session).find_all_active()

    cron_parts = settings.pipeline_schedule.split()
    trigger = CronTrigger(
        minute=cron_parts[0],
        hour=cron_parts[1],
        day=cron_parts[2],
        month=cron_parts[3],
        day_of_week=cron_parts[4],
    )

    for niche in niches:
        job_id = f"pipeline_{niche.id}"
        if not scheduler.get_job(job_id):
            scheduler.add_job(
                _run_pipeline_for_niche,
                trigger=trigger,
                args=[str(niche.id)],
                id=job_id,
                coalesce=True,
                max_instances=1,
            )
            logger.info("Scheduled pipeline job for niche_id=%s", niche.id)

        add_product_discovery_job(niche)


def add_niche_job(niche_id_str: str) -> None:
    cron_parts = settings.pipeline_schedule.split()
    trigger = CronTrigger(
        minute=cron_parts[0],
        hour=cron_parts[1],
        day=cron_parts[2],
        month=cron_parts[3],
        day_of_week=cron_parts[4],
    )
    job_id = f"pipeline_{niche_id_str}"
    scheduler.add_job(
        _run_pipeline_for_niche,
        trigger=trigger,
        args=[niche_id_str],
        id=job_id,
        coalesce=True,
        max_instances=1,
        replace_existing=True,
    )


def add_product_discovery_job(niche: object) -> None:
    discovery_mode = getattr(niche, "discovery_mode", "content")
    if discovery_mode not in ("product", "both"):
        return

    niche_id_str = str(niche.id)  # type: ignore[union-attr]
    cron_parts = settings.pipeline_schedule.split()
    trigger = CronTrigger(
        minute=cron_parts[0],
        hour=cron_parts[1],
        day=cron_parts[2],
        month=cron_parts[3],
        day_of_week=cron_parts[4],
    )
    job_id = f"product_pipeline_{niche_id_str}"
    scheduler.add_job(
        _run_product_pipeline_for_niche,
        trigger=trigger,
        args=[niche_id_str],
        id=job_id,
        coalesce=True,
        max_instances=1,
        replace_existing=True,
    )
    logger.info("Scheduled product discovery job for niche_id=%s", niche_id_str)


def remove_niche_job(niche_id_str: str) -> None:
    job_id = f"pipeline_{niche_id_str}"
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
