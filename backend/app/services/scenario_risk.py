from __future__ import annotations

from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import ScenarioTemplate
from app.schemas.treasury import ReverseStressOut, ScenarioTemplateOut
from app.services.forecast import calculate_custom_liquidity_forecast


def list_scenario_templates(db: Session) -> list[ScenarioTemplateOut]:
    rows = db.scalars(select(ScenarioTemplate).where(ScenarioTemplate.active.is_(True)).order_by(ScenarioTemplate.scenario_code)).all()
    return [ScenarioTemplateOut(
        scenario_code=x.scenario_code,
        label=x.label,
        receivable_multiplier=Decimal(x.receivable_multiplier),
        payable_multiplier=Decimal(x.payable_multiplier),
        facility_availability=Decimal(x.facility_availability),
        fx_shock_pct=Decimal(x.fx_shock_pct),
        rate_shock_bps=x.rate_shock_bps,
    ) for x in rows]


def reverse_stress_collections(
    db: Session,
    weeks: int = 13,
    payable_multiplier: Decimal = Decimal("1.10"),
    facility_availability: Decimal = Decimal("0.75"),
    iterations: int = 24,
) -> ReverseStressOut:
    """Find the approximate receivable realization multiplier where liquidity first breaches the buffer.

    Other stress dimensions stay fixed and explicit. The search is deterministic and intended for
    reverse-stress discovery, not probability estimation.
    """
    low = Decimal("0")
    high = Decimal("1")

    high_result = calculate_custom_liquidity_forecast(db, high, payable_multiplier, facility_availability, weeks, "Reverse-stress high")
    low_result = calculate_custom_liquidity_forecast(db, low, payable_multiplier, facility_availability, weeks, "Reverse-stress low")

    if high_result.first_buffer_breach_week is not None:
        threshold = high
        result = high_result
        trigger = "BREACH_EVEN_WITH_FULL_COLLECTIONS"
    elif low_result.first_buffer_breach_week is None:
        threshold = low
        result = low_result
        trigger = "NO_BREACH_WITH_ZERO_COLLECTIONS"
    else:
        # low breaches, high survives. Find the boundary: smallest multiplier that survives.
        for _ in range(iterations):
            mid = (low + high) / Decimal("2")
            mid_result = calculate_custom_liquidity_forecast(db, mid, payable_multiplier, facility_availability, weeks, "Reverse-stress search")
            if mid_result.first_buffer_breach_week is None:
                high = mid
            else:
                low = mid
        threshold = low
        result = calculate_custom_liquidity_forecast(db, threshold, payable_multiplier, facility_availability, weeks, "Reverse-stress threshold")
        trigger = "COLLECTION_HAIRCUT_THRESHOLD"

    return ReverseStressOut(
        reporting_currency=settings.group_reporting_currency,
        weeks=weeks,
        trigger=trigger,
        receivable_multiplier=threshold,
        collection_haircut_pct=(Decimal("1") - threshold) * Decimal("100"),
        payable_multiplier=Decimal(payable_multiplier),
        facility_availability=Decimal(facility_availability),
        first_buffer_breach_week=result.first_buffer_breach_week,
        maximum_shortfall=result.maximum_shortfall,
        ending_liquidity_headroom=result.ending_liquidity_headroom,
        iterations=iterations,
    )
