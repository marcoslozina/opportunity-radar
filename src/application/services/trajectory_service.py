from __future__ import annotations

from domain.entities.briefing import Briefing
from domain.value_objects.score_trajectory import ScoreTrajectory


class TrajectoryService:
    def compute(
        self,
        current: Briefing,
        previous: Briefing | None,
    ) -> dict[str, ScoreTrajectory]:
        """
        Returns a mapping of normalized_topic -> ScoreTrajectory.
        Only topics present in BOTH briefings are included.
        Topics with no match in previous are absent from the result
        (caller treats missing key as trajectory=None).
        """
        if previous is None:
            return {}

        previous_index: dict[str, float] = {
            opp.topic.lower().strip(): opp.score.total
            for opp in previous.opportunities
        }

        result: dict[str, ScoreTrajectory] = {}
        for opp in current.opportunities:
            key = opp.topic.lower().strip()
            if key in previous_index:
                result[key] = ScoreTrajectory.compute(
                    current_total=opp.score.total,
                    previous_total=previous_index[key],
                    compared_at=previous.generated_at,
                )
        return result
