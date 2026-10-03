from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import DerivativePosition
from app.schemas.treasury import FXStressRow, MarketStressOut
from app.services.derivative_risk import calculate_interest_rate_risk
from app.services.exposure import calculate_fx_exposures
from app.services.fx import FXConversionError, convert

ZERO = Decimal("0")


def calculate_market_stress(
    db: Session,
    fx_shock_pct: Decimal = Decimal("0.10"),
    rate_shock_bps: int = 100,
) -> MarketStressOut:
    """Deterministic adverse market overlay.

    FX uses residual economic exposure after derivative hedges. The adverse change is
    deliberately direction-agnostic: it estimates the loss magnitude from a shock against
    the group. Interest-rate impact is calculated only on residual floating-rate debt.
    This is a sensitivity, not VaR and not a derivative pricing model.
    """
    fx_rows: list[FXStressRow] = []
    warnings: list[str] = []
    total_fx_adverse = ZERO

    for row in calculate_fx_exposures(db):
        if row.currency == settings.group_reporting_currency:
            continue
        try:
            residual_reporting = convert(
                db,
                Decimal(row.residual_exposure),
                row.currency,
                settings.group_reporting_currency,
            )
        except FXConversionError as exc:
            warnings.append(str(exc))
            continue
        adverse = abs(residual_reporting) * fx_shock_pct
        total_fx_adverse += adverse
        fx_rows.append(FXStressRow(
            currency=row.currency,
            residual_exposure_local=Decimal(row.residual_exposure),
            residual_exposure_reporting=residual_reporting,
            adverse_shock_pct=fx_shock_pct,
            estimated_adverse_value_change=adverse,
        ))

    rate = calculate_interest_rate_risk(db)
    annual_rate_impact = rate.residual_floating_exposure * Decimal(rate_shock_bps) / Decimal("10000")

    # Near-term negative MTM is a conservative liquidity call proxy for settlements/margin.
    horizon = date.today() + timedelta(days=30)
    near_term_negative_mtm = ZERO
    for trade in db.scalars(select(DerivativePosition).where(
        DerivativePosition.status == "OPEN",
        DerivativePosition.maturity_date <= horizon,
    )).all():
        mtm = Decimal(trade.market_value_reporting_ccy)
        if mtm < 0:
            near_term_negative_mtm += abs(mtm)

    # One-quarter of annualized rate sensitivity is used as a 13-week liquidity overlay.
    quarter_rate_impact = annual_rate_impact / Decimal("4")
    combined_call = total_fx_adverse + quarter_rate_impact + near_term_negative_mtm

    if total_fx_adverse > Decimal("5000000"):
        warnings.append("Adverse FX sensitivity exceeds 5m in group reporting currency.")
    if near_term_negative_mtm > ZERO:
        warnings.append("Negative derivative MTM matures within 30 days and may create settlement or collateral liquidity demand.")

    return MarketStressOut(
        reporting_currency=settings.group_reporting_currency,
        fx_shock_pct=fx_shock_pct,
        rate_shock_bps=rate_shock_bps,
        estimated_fx_adverse_change=total_fx_adverse,
        annual_rate_cash_impact=annual_rate_impact,
        near_term_derivative_negative_mtm=near_term_negative_mtm,
        combined_market_liquidity_call=combined_call,
        fx_rows=fx_rows,
        warnings=warnings,
    )
