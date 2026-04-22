from __future__ import annotations

from abc import ABC, abstractmethod

from domain.value_objects.trend_signal import TrendSignal


class TrendDataPort(ABC):
    @abstractmethod
    async def collect(self, keywords: list[str]) -> list[TrendSignal]: ...
