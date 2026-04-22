from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID, uuid4


@dataclass(frozen=True)
class NicheId:
    value: UUID

    def __str__(self) -> str:
        return str(self.value)


@dataclass
class Niche:
    id: NicheId
    name: str
    keywords: list[str]
    active: bool = field(default=True)
    discovery_mode: str = field(default="content")

    @classmethod
    def create(cls, name: str, keywords: list[str], discovery_mode: str = "content") -> Niche:
        return cls(id=NicheId(uuid4()), name=name, keywords=keywords, discovery_mode=discovery_mode)
