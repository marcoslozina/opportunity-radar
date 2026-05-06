from __future__ import annotations

import json
from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class NicheModel(Base):
    __tablename__ = "niches"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    keywords_json: Mapped[str] = mapped_column(Text, nullable=False)
    active: Mapped[bool] = mapped_column(default=True)
    discovery_mode: Mapped[str] = mapped_column(String(10), nullable=False, default="content", server_default="content")
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
    frustration_level: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0.0")
    total: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[str] = mapped_column(String(10), nullable=False)
    recommended_action: Mapped[str] = mapped_column(Text, default="")
    domain_applicability: Mapped[str] = mapped_column(String(50), nullable=False, default="", server_default="")
    domain_reasoning: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    evidence_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]", server_default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    briefing: Mapped[BriefingModel] = relationship(
        "BriefingModel", back_populates="opportunities"
    )


class ProductOpportunityModel(Base):
    __tablename__ = "product_opportunities"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    niche_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("niches.id", ondelete="CASCADE"), nullable=False
    )
    briefing_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("product_briefings.id", ondelete="CASCADE"), nullable=True
    )
    topic: Mapped[str] = mapped_column(String(500), nullable=False)
    frustration_level: Mapped[float | None] = mapped_column(Float, nullable=True)
    market_size: Mapped[float | None] = mapped_column(Float, nullable=True)
    competition_gap: Mapped[float | None] = mapped_column(Float, nullable=True)
    willingness_to_pay: Mapped[float | None] = mapped_column(Float, nullable=True)
    total: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence: Mapped[str | None] = mapped_column(String(10), nullable=True)
    product_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    product_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommended_price_range: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    briefing: Mapped[ProductBriefingModel | None] = relationship(
        "ProductBriefingModel", back_populates="opportunities"
    )


class ProductBriefingModel(Base):
    __tablename__ = "product_briefings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    niche_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("niches.id", ondelete="CASCADE"), nullable=False
    )
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    opportunities: Mapped[list[ProductOpportunityModel]] = relationship(
        "ProductOpportunityModel", back_populates="briefing", cascade="all, delete-orphan"
    )


class ApiKeyModel(Base):
    __tablename__ = "api_keys"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    client_name: Mapped[str] = mapped_column(String(255), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    scopes_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_api_keys_key_hash", "key_hash"),
        Index("ix_api_keys_client_name", "client_name"),
    )

    @property
    def scopes(self) -> list[str]:
        return json.loads(self.scopes_json)  # type: ignore[no-any-return]

    @scopes.setter
    def scopes(self, value: list[str]) -> None:
        self.scopes_json = json.dumps(value)
