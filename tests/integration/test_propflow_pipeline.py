import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from domain.entities.niche import Niche, NicheId
from application.use_cases.run_pipeline import RunPipelineUseCase

@pytest.mark.asyncio
async def test_run_real_estate_pipeline_integration():
    # Setup
    niche_repo = MagicMock()
    briefing_repo = AsyncMock()
    collector = MagicMock()
    insight_port = AsyncMock()

    niche = Niche.create(
        name="Real Estate Test",
        keywords=["prop1"], 
        discovery_mode="real_estate"
    )
    niche_repo.find_by_id = AsyncMock(return_value=niche)
    
    from domain.value_objects.trend_signal import TrendSignal
    from datetime import datetime, timezone
    now = datetime.now(tz=timezone.utc)
    
    collector.collect = AsyncMock(return_value=[
        TrendSignal(source="s1", topic="t1", raw_value=0.8, signal_type="trend_velocity", collected_at=now),
        TrendSignal(source="s1", topic="t1", raw_value=0.7, signal_type="monetization_intent", collected_at=now),
    ])
    
    use_case = RunPipelineUseCase(
        niche_repo=niche_repo,
        briefing_repo=briefing_repo,
        collectors=[collector],
        insight_port=insight_port
    )
    
    # Execute
    await use_case.execute(niche.id)
    
    # Assert
    assert insight_port.synthesize.called
    # Check that it passed 'real_estate' to synthesize
    args, kwargs = insight_port.synthesize.call_args
    assert args[1] == "real_estate"
    
    assert briefing_repo.save.called
    briefing = briefing_repo.save.call_args[0][0]
    assert len(briefing.opportunities) == 1
    assert briefing.opportunities[0].topic == "t1"
