from __future__ import annotations

import json
from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class NicheModel(Base):
    __tablename__ = "niches"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    keywords_json: Mapped[str] = mapped_column(Text, nullable=False)
    active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    briefings: Mapped[list[BriefingModel]] = relationship(
        "BriefingModel", back_populates="niche", cascade="all, delete-orphan"
    )

    @property
    def keywords(self) -> list[str]:
        return json.loads(self.keywords_json)

    @keywords.setter
    def keywords(self, value: list[str]) -> None:
        self.keywords_json = json.dumps(value)


class BriefingModel(Base):
    __tablename__ = "briefings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    niche_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("niches.id", ondelete="CASCADE"), nullable=False
    )
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    niche: Mapped[NicheModel] = relationship("NicheModel", back_populates="briefings")
    opportunities: Mapped[list[OpportunityModel]] = relationship(
        "OpportunityModel", back_populates="briefing", cascade="all, delete-orphan"
    )


class OpportunityModel(Base):
    __tablename__ = "opportunities"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    briefing_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("briefings.id", ondelete="CASCADE"), nullable=False
    )
    topic: Mapped[str] = mapped_column(String(500), nullable=False)
    trend_velocity: Mapped[float] = mapped_column(Float, nullable=False)
    competition_gap: Mapped[float] = mapped_column(Float, nullable=False)
    social_signal: Mapped[float] = mapped_column(Float, nullable=False)
    monetization_intent: Mapped[float] = mapped_column(Float, nullable=False)
    total: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[str] = mapped_column(String(10), nullable=False)
    recommended_action: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    briefing: Mapped[BriefingModel] = relationship(
        "BriefingModel", back_populates="opportunities"
    )
