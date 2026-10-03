from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.config import settings
from app.schemas.treasury import IntegratedScenarioOut, IntegratedScenarioRequest
from app.services.forecast import calculate_custom_liquidity_forecast
from app.services.global_treasury import calculate_collateral_liquidity, calculate_refinancing_risk
from app.services.market_stress import calculate_market_stress

ZERO = Decimal("0")


def calculate_integrated_scenario(db: Session, request: IntegratedScenarioRequest) -> IntegratedScenarioOut:
    forecast = calculate_custom_liquidity_forecast(
        db,
        receivable_multiplier=request.receivable_multiplier,
        payable_multiplier=request.payable_multiplier,
        facility_availability=request.facility_availability,
        weeks=request.weeks,
        label=request.label,
    )
    market = calculate_market_stress(db, request.fx_shock_pct, request.rate_shock_bps)
    collateral = calculate_collateral_liquidity(db)
    refinancing = calculate_refinancing_risk(db)

    horizon_fraction = Decimal(request.weeks) / Decimal("52")
    annual_rate_cash = Decimal(market.annual_rate_cash_impact)
    rate_cash_horizon = annual_rate_cash * horizon_fraction

    current_margin = Decimal(collateral.current_margin_call)
    stressed_margin = Decimal(collateral.stressed_margin_call)
    incremental_margin = max(stressed_margin - current_margin, ZERO) * max(request.collateral_stress_multiplier, ZERO)
    derivative_liquidity_call = max(Decimal(market.near_term_derivative_negative_mtm), incremental_margin)

    refinancing_base = Decimal(refinancing.debt_due_180d)
    incremental_refi_cost = (
        refinancing_base
        * Decimal(request.refinancing_spread_shock_bps)
        / Decimal("10000")
        * horizon_fraction
    )

    stressed_headroom = (
        Decimal(forecast.ending_liquidity_headroom)
        - rate_cash_horizon
        - derivative_liquidity_call
        - incremental_refi_cost
    )
    status = "BREACH" if stressed_headroom < 0 else "WATCH" if stressed_headroom < Decimal(forecast.maximum_shortfall) + Decimal("10000000") else "RESILIENT"

    notes = [
        "FX adverse change is reported as economic value sensitivity and is not automatically treated as a cash outflow.",
        "Derivative settlement and collateral calls may overlap; the larger of the two is used to reduce double counting.",
        "Refinancing spread shock is modeled as incremental interest cost over the scenario horizon, not principal repayment.",
        "Scenario output is a treasury stress estimate and not a market-value or accounting forecast.",
    ]

    return IntegratedScenarioOut(
        label=request.label,
        reporting_currency=settings.group_reporting_currency,
        weeks=request.weeks,
        forecast_ending_headroom=Decimal(forecast.ending_liquidity_headroom),
        forecast_maximum_shortfall=Decimal(forecast.maximum_shortfall),
        first_buffer_breach_week=forecast.first_buffer_breach_week,
        fx_economic_value_sensitivity=Decimal(market.estimated_fx_adverse_change),
        rate_cash_impact_horizon=rate_cash_horizon,
        derivative_or_collateral_liquidity_call=derivative_liquidity_call,
        incremental_refinancing_cost_horizon=incremental_refi_cost,
        stressed_liquidity_headroom_after_overlays=stressed_headroom,
        status=status,
        component_notes=notes,
    )
