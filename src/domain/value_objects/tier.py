from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Literal

TierName = Literal["starter", "professional", "enterprise"]


@dataclass(frozen=True)
class TierInfo:
    name: TierName
    max_opportunities_month: int  # -1 = unlimited
    max_niches: int               # nichos monitoreados simultáneamente
    max_alert_rules: int          # reglas de alerta configuradas
    briefings: bool               # acceso a briefings detallados
    product_discovery: bool       # feature de product discovery (Claude)
    export_csv: bool              # exportar datos en CSV
    rate_limit_per_minute: int    # requests por minuto


TIERS: dict[str, TierInfo] = {
    "starter": TierInfo(
        name="starter",
        max_opportunities_month=100,
        max_niches=3,
        max_alert_rules=5,
        briefings=False,
        product_discovery=False,
        export_csv=False,
        rate_limit_per_minute=20,
    ),
    "professional": TierInfo(
        name="professional",
        max_opportunities_month=1000,
        max_niches=15,
        max_alert_rules=25,
        briefings=True,
        product_discovery=True,
        export_csv=True,
        rate_limit_per_minute=60,
    ),
    "enterprise": TierInfo(
        name="enterprise",
        max_opportunities_month=-1,
        max_niches=-1,
        max_alert_rules=-1,
        briefings=True,
        product_discovery=True,
        export_csv=True,
        rate_limit_per_minute=300,
    ),
}


VALID_TIERS: frozenset[str] = frozenset(TIERS.keys())  # {"starter", "professional", "enterprise"}


def get_tier(name: str) -> TierInfo:
    if name not in TIERS:
        raise ValueError(
            f"[TIER] Unknown tier name: '{name}'. Valid tiers: {sorted(VALID_TIERS)}"
        )
    return TIERS[name]
