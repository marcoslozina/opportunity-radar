from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class EvidenceItem:
    source: str           # "reddit" | "hacker_news" | "serp" | "youtube"
    signal_type: str      # mirrors TrendSignal.signal_type
    topic: str            # same keyword that produced the signal
    title: str            # human-readable label for the evidence item
    url: str | None       # direct link to the source item; None for numeric signals
    engagement_count: int # upvotes, points, search rank, etc.
    engagement_label: str # "upvotes" | "points" | "rank" | "ad_position" | "search_rank"
    collected_at: datetime
