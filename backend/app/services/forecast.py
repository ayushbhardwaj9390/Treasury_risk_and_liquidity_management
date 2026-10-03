from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import CashFlow
from app.schemas.treasury import ForecastPoint, LiquidityForecastOut, StressScenarioSummary
from app.services.fx import FXConversionError, convert
from app.services.liquidity import calculate_global_liquidity

ZERO = Decimal("0")
ONE = Decimal("1")


@dataclass(frozen=True)
class Scenario:
    code: str
    label: str
    receivable_multiplier: Decimal
    payable_multiplier: Decimal
    facility_availability: Decimal


SCENARIOS: dict[str, Scenario] = {
    "BASE": Scenario("BASE", "Base", Decimal("1.00"), Decimal("1.00"), Decimal("1.00")),
    "MODERATE": Scenario("MODERATE", "Moderate stress", Decimal("0.85"), Decimal("1.05"), Decimal("0.90")),
    "SEVERE": Scenario("SEVERE", "Severe stress", Decimal("0.60"), Decimal("1.25"), Decimal("0.25")),
}


def _week_bounds(start: date, week_number: int) -> tuple[date, date]:
    week_start = start + timedelta(days=(week_number - 1) * 7)
    return week_start, week_start + timedelta(days=6)


def _reporting_amount(db: Session, amount: Decimal, currency: str) -> Decimal:
    return convert(db, amount, currency, settings.group_reporting_currency)


def _calculate_forecast(
    db: Session,
    scenario: Scenario,
    weeks: int = 13,
    start_date: date | None = None,
) -> LiquidityForecastOut:
    if weeks < 1 or weeks > 52:
        raise ValueError("weeks must be between 1 and 52")

    start = start_date or date.today()
    current = calculate_global_liquidity(db)
    opening_cash = Decimal(current.deployable_cash)
    minimum_buffer = Decimal(current.minimum_cash)
    base_undrawn = Decimal(current.undrawn_credit)
    available_facility = base_undrawn * scenario.facility_availability

    horizon_end = start + timedelta(days=weeks * 7 - 1)
    flows = db.scalars(
        select(CashFlow).where(
            CashFlow.status == "OPEN",
            CashFlow.due_date >= start,
            CashFlow.due_date <= horizon_end,
        )
    ).all()

    warnings: list[str] = []
    points: list[ForecastPoint] = []
    cash = opening_cash
    first_breach_week: int | None = None
    max_shortfall = ZERO

    for week in range(1, weeks + 1):
        week_start, week_end = _week_bounds(start, week)
        inflows = ZERO
        outflows = ZERO

        for flow in flows:
            if not (week_start <= flow.due_date <= week_end):
                continue
            try:
                amount_reporting = _reporting_amount(db, Decimal(flow.amount), flow.currency)
            except FXConversionError as exc:
                warnings.append(str(exc))
                continue

            if flow.flow_type == "RECEIVABLE":
                probability = min(max(Decimal(flow.probability), ZERO), ONE)
                inflows += amount_reporting * probability * scenario.receivable_multiplier
            elif flow.flow_type == "PAYABLE":
                outflows += amount_reporting * scenario.payable_multiplier

        closing_cash = cash + inflows - outflows
        effective_liquidity = closing_cash + available_facility
        headroom = effective_liquidity - minimum_buffer
        shortfall = max(-headroom, ZERO)

        if shortfall > ZERO and first_breach_week is None:
            first_breach_week = week
        max_shortfall = max(max_shortfall, shortfall)

        points.append(
            ForecastPoint(
                week=week,
                week_start=week_start,
                week_end=week_end,
                opening_cash=cash,
                expected_inflows=inflows,
                expected_outflows=outflows,
                closing_cash=closing_cash,
                available_facility=available_facility,
                minimum_buffer=minimum_buffer,
                liquidity_headroom=headroom,
                shortfall=shortfall,
            )
        )
        cash = closing_cash

    return LiquidityForecastOut(
        scenario=scenario.code,
        scenario_label=scenario.label,
        reporting_currency=settings.group_reporting_currency,
        start_date=start,
        weeks=weeks,
        receivable_multiplier=scenario.receivable_multiplier,
        payable_multiplier=scenario.payable_multiplier,
        facility_availability=scenario.facility_availability,
        first_buffer_breach_week=first_breach_week,
        maximum_shortfall=max_shortfall,
        ending_cash=cash,
        ending_liquidity_headroom=points[-1].liquidity_headroom if points else ZERO,
        points=points,
        warnings=sorted(set(warnings)),
    )


def calculate_liquidity_forecast(
    db: Session,
    scenario_code: str = "BASE",
    weeks: int = 13,
    start_date: date | None = None,
) -> LiquidityForecastOut:
    scenario = SCENARIOS.get(scenario_code.upper())
    if scenario is None:
        raise ValueError(f"Unknown scenario: {scenario_code}")
    return _calculate_forecast(db, scenario, weeks, start_date)


def calculate_custom_liquidity_forecast(
    db: Session,
    receivable_multiplier: Decimal,
    payable_multiplier: Decimal,
    facility_availability: Decimal,
    weeks: int = 13,
    label: str = "Custom scenario",
) -> LiquidityForecastOut:
    scenario = Scenario(
        code="CUSTOM",
        label=label,
        receivable_multiplier=max(Decimal(receivable_multiplier), ZERO),
        payable_multiplier=max(Decimal(payable_multiplier), ZERO),
        facility_availability=min(max(Decimal(facility_availability), ZERO), ONE),
    )
    return _calculate_forecast(db, scenario, weeks)


def calculate_stress_summary(db: Session, weeks: int = 13) -> list[StressScenarioSummary]:
    results: list[StressScenarioSummary] = []
    for code in ("BASE", "MODERATE", "SEVERE"):
        forecast = calculate_liquidity_forecast(db, code, weeks)
        minimum_headroom = min((p.liquidity_headroom for p in forecast.points), default=ZERO)
        results.append(
            StressScenarioSummary(
                scenario=forecast.scenario,
                scenario_label=forecast.scenario_label,
                ending_cash=forecast.ending_cash,
                minimum_headroom=minimum_headroom,
                maximum_shortfall=forecast.maximum_shortfall,
                first_buffer_breach_week=forecast.first_buffer_breach_week,
            )
        )
    return results
