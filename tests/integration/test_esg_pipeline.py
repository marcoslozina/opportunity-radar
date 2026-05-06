import pytest
from unittest.mock import AsyncMock, MagicMock
from domain.entities.niche import Niche
from application.use_cases.run_pipeline import RunPipelineUseCase
from domain.value_objects.trend_signal import TrendSignal
from datetime import datetime, timezone


@pytest.mark.asyncio
async def test_run_esg_pipeline_integration():
    # Setup
    niche_repo = MagicMock()
    briefing_repo = AsyncMock()
    collector = MagicMock()
    insight_port = AsyncMock()
    
    niche = Niche.create(
        name="ESG Test", 
        keywords=["esg1"], 
        discovery_mode="esg_intelligence"
    )
    niche_repo.find_by_id = AsyncMock(return_value=niche)
    
    now = datetime.now(tz=timezone.utc)
    
    # We want to verify that ESGScoringEngine is used (via factory)
    # ESG weights focus more on competition_gap (0.30)
    collector.collect = AsyncMock(return_value=[
        TrendSignal(source="s1", topic="Carbon Tax", raw_value=0.9, signal_type="competition_gap", collected_at=now),
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
    # Verify synthesize was called with 'esg_intelligence'
    insight_port.synthesize.assert_called_once()
    args, _ = insight_port.synthesize.call_args
    assert args[1] == "esg_intelligence"
    
    # Verify the score matches ESG logic
    # Score = (0.9 * 0.30) * 10 = 2.7 * 10 = 27
    briefing = briefing_repo.save.call_args[0][0]
    opp = briefing.opportunities[0]
    assert opp.score.total == 27.0
    assert opp.score.competition_gap == 9.0
