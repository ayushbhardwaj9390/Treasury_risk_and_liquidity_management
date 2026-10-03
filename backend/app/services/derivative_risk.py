from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import CashFlow, CounterpartyLimit, DebtPosition, DerivativePosition, LegalEntity, TreasuryPolicy
from app.schemas.treasury import (
    CounterpartyExposureRow,
    DerivativeMaturityBucket,
    DerivativePositionOut,
    DerivativeRiskSummary,
    HedgeCoverageRow,
    InterestRateRiskOut,
)
from app.services.fx import FXConversionError, convert

ZERO = Decimal("0")
ONE = Decimal("1")

PFE_FACTORS = {
    "FX_FORWARD": Decimal("0.05"),
    "FX_OPTION": Decimal("0.075"),
    "FX_SWAP": Decimal("0.05"),
    "INTEREST_RATE_SWAP": Decimal("0.03"),
    "CROSS_CURRENCY_SWAP": Decimal("0.06"),
}


def _policy(db: Session, code: str, default: Decimal) -> Decimal:
    row = db.scalar(select(TreasuryPolicy).where(TreasuryPolicy.policy_code == code, TreasuryPolicy.active.is_(True)))
    return Decimal(row.threshold_value) if row and row.threshold_value is not None else default


def list_derivatives(db: Session) -> list[DerivativePositionOut]:
    entities = {e.id: e.name for e in db.scalars(select(LegalEntity)).all()}
    rows: list[DerivativePositionOut] = []
    for trade in db.scalars(select(DerivativePosition).where(DerivativePosition.status == "OPEN").order_by(DerivativePosition.maturity_date)).all():
        try:
            notional_reporting = convert(db, Decimal(trade.notional), trade.exposure_currency, settings.group_reporting_currency)
        except FXConversionError:
            notional_reporting = ZERO
        rows.append(DerivativePositionOut(
            id=trade.id,
            entity_name=entities.get(trade.entity_id, f"Entity {trade.entity_id}"),
            instrument_type=trade.instrument_type,
            counterparty=trade.counterparty,
            exposure_currency=trade.exposure_currency,
            notional=Decimal(trade.notional),
            notional_reporting=notional_reporting,
            hedge_direction=trade.hedge_direction,
            maturity_date=trade.maturity_date,
            days_to_maturity=max((trade.maturity_date - date.today()).days, 0),
            market_value_reporting_ccy=Decimal(trade.market_value_reporting_ccy),
            hedge_designation=trade.hedge_designation,
            underlying_reference=trade.underlying_reference,
            mapped_to_underlying=bool(trade.underlying_reference or trade.hedge_designation),
        ))
    return rows


def derivative_risk_summary(db: Session) -> DerivativeRiskSummary:
    trades = list_derivatives(db)
    buckets = {
        "0-30d": [0, ZERO, ZERO],
        "31-90d": [0, ZERO, ZERO],
        "91-180d": [0, ZERO, ZERO],
        "181-365d": [0, ZERO, ZERO],
        ">365d": [0, ZERO, ZERO],
    }
    warnings: list[str] = []
    total_notional = net_mtm = positive_mtm = negative_mtm = ZERO
    unmapped = 0

    for trade in trades:
        total_notional += abs(trade.notional_reporting)
        net_mtm += trade.market_value_reporting_ccy
        positive_mtm += max(trade.market_value_reporting_ccy, ZERO)
        negative_mtm += min(trade.market_value_reporting_ccy, ZERO)
        if not trade.mapped_to_underlying:
            unmapped += 1

        d = trade.days_to_maturity
        bucket = "0-30d" if d <= 30 else "31-90d" if d <= 90 else "91-180d" if d <= 180 else "181-365d" if d <= 365 else ">365d"
        buckets[bucket][0] += 1
        buckets[bucket][1] += abs(trade.notional_reporting)
        buckets[bucket][2] += trade.market_value_reporting_ccy

    if unmapped:
        warnings.append(f"{unmapped} open derivative trade(s) are not mapped to an approved underlying exposure.")
    if trades and sum(1 for t in trades if t.days_to_maturity <= 30) >= 2:
        warnings.append("Multiple derivative maturities fall within the next 30 days; settlement liquidity should be confirmed.")

    maturity_rows = [
        DerivativeMaturityBucket(bucket=k, trade_count=v[0], notional_reporting=v[1], market_value_reporting_ccy=v[2])
        for k, v in buckets.items()
    ]
    return DerivativeRiskSummary(
        reporting_currency=settings.group_reporting_currency,
        open_trade_count=len(trades),
        total_notional_reporting=total_notional,
        net_market_value_reporting=net_mtm,
        positive_market_value_reporting=positive_mtm,
        negative_market_value_reporting=negative_mtm,
        unmapped_trade_count=unmapped,
        maturity_buckets=maturity_rows,
        warnings=warnings,
    )


def calculate_hedge_coverage(db: Session) -> list[HedgeCoverageRow]:
    underlying = defaultdict(lambda: ZERO)
    hedges = defaultdict(lambda: ZERO)

    for flow in db.scalars(select(CashFlow).where(CashFlow.status == "OPEN")).all():
        expected = Decimal(flow.amount) * Decimal(flow.probability)
        underlying[flow.currency] += expected if flow.flow_type == "RECEIVABLE" else -expected

    for trade in db.scalars(select(DerivativePosition).where(DerivativePosition.status == "OPEN")).all():
        if not trade.instrument_type.startswith("FX_") and trade.instrument_type != "CROSS_CURRENCY_SWAP":
            continue
        sign = ONE if trade.hedge_direction == "BUY" else Decimal("-1")
        hedges[trade.exposure_currency] += sign * Decimal(trade.notional)

    policy_min = _policy(db, "FX_HEDGE_RATIO_MIN", Decimal("0.60"))
    policy_max = _policy(db, "FX_HEDGE_RATIO_MAX", Decimal("0.90"))
    rows: list[HedgeCoverageRow] = []
    for currency in sorted(set(underlying) | set(hedges)):
        gross = underlying[currency]
        hedge = hedges[currency]
        residual = gross + hedge
        if gross == 0:
            ratio = None
            status = "UNMATCHED" if hedge != 0 else "NO_EXPOSURE"
        else:
            ratio = min(abs(hedge) / abs(gross), Decimal("9.999999"))
            if abs(hedge) > abs(gross) * Decimal("1.05"):
                status = "OVER-HEDGED"
            elif ratio < policy_min:
                status = "UNDER-HEDGED"
            elif ratio > policy_max:
                status = "ABOVE-POLICY"
            else:
                status = "WITHIN-POLICY"
        rows.append(HedgeCoverageRow(
            currency=currency,
            underlying_exposure=gross,
            hedge_notional=hedge,
            hedge_ratio=ratio,
            residual_exposure=residual,
            policy_min=policy_min,
            policy_max=policy_max,
            status=status,
        ))
    return rows


def calculate_counterparty_exposure(db: Session) -> list[CounterpartyExposureRow]:
    limits = {x.counterparty: x for x in db.scalars(select(CounterpartyLimit).where(CounterpartyLimit.active.is_(True))).all()}
    grouped = defaultdict(lambda: {"mtm": ZERO, "pfe": ZERO})

    for trade in db.scalars(select(DerivativePosition).where(DerivativePosition.status == "OPEN")).all():
        positive_mtm = max(Decimal(trade.market_value_reporting_ccy), ZERO)
        try:
            notional_reporting = abs(convert(db, Decimal(trade.notional), trade.exposure_currency, settings.group_reporting_currency))
        except FXConversionError:
            notional_reporting = ZERO
        factor = PFE_FACTORS.get(trade.instrument_type, Decimal("0.05"))
        grouped[trade.counterparty]["mtm"] += positive_mtm
        grouped[trade.counterparty]["pfe"] += notional_reporting * factor

    rows: list[CounterpartyExposureRow] = []
    for counterparty, values in sorted(grouped.items()):
        limit_row = limits.get(counterparty)
        limit = Decimal(limit_row.exposure_limit_reporting_ccy) if limit_row else ZERO
        exposure = values["mtm"] + values["pfe"]
        utilization = exposure / limit if limit > 0 else ZERO
        if limit <= 0:
            status = "NO-LIMIT"
        elif utilization >= ONE:
            status = "BREACH"
        elif utilization >= Decimal(limit_row.warning_utilization):
            status = "WARNING"
        else:
            status = "WITHIN-LIMIT"
        rows.append(CounterpartyExposureRow(
            counterparty=counterparty,
            credit_rating=limit_row.credit_rating if limit_row else None,
            current_positive_mtm=values["mtm"],
            potential_future_exposure=values["pfe"],
            credit_exposure=exposure,
            exposure_limit=limit,
            utilization=utilization,
            status=status,
        ))
    return rows


def calculate_interest_rate_risk(db: Session) -> InterestRateRiskOut:
    total = fixed = floating = ZERO
    warnings: list[str] = []
    for debt in db.scalars(select(DebtPosition).where(DebtPosition.status == "OPEN")).all():
        try:
            principal = convert(db, Decimal(debt.principal), debt.currency, settings.group_reporting_currency)
        except FXConversionError as exc:
            warnings.append(str(exc))
            continue
        total += principal
        if debt.rate_type == "FLOATING":
            floating += principal
        else:
            fixed += principal

    pay_fixed = ZERO
    for trade in db.scalars(select(DerivativePosition).where(
        DerivativePosition.status == "OPEN",
        DerivativePosition.instrument_type == "INTEREST_RATE_SWAP",
        DerivativePosition.hedge_direction == "PAY_FIXED",
    )).all():
        try:
            pay_fixed += abs(convert(db, Decimal(trade.notional), trade.exposure_currency, settings.group_reporting_currency))
        except FXConversionError as exc:
            warnings.append(str(exc))

    residual_floating = max(floating - pay_fixed, ZERO)
    pre_share = floating / total if total else ZERO
    post_share = residual_floating / total if total else ZERO
    max_share = _policy(db, "MAX_FLOATING_RATE_SHARE", Decimal("0.50"))
    if post_share > max_share:
        warnings.append(f"Residual floating-rate share {post_share:.1%} exceeds policy maximum {max_share:.1%}.")

    return InterestRateRiskOut(
        reporting_currency=settings.group_reporting_currency,
        total_debt=total,
        fixed_rate_debt=fixed,
        floating_rate_debt=floating,
        pay_fixed_swap_notional=pay_fixed,
        residual_floating_exposure=residual_floating,
        floating_share_before_hedges=pre_share,
        floating_share_after_hedges=post_share,
        annual_cash_impact_100bps=residual_floating * Decimal("0.01"),
        annual_cash_impact_200bps=residual_floating * Decimal("0.02"),
        warnings=warnings,
    )


def update_derivative_mtm(db: Session, updates, actor: str = "TREASURY_MARKET_DATA"):
    """Persist externally valued MTM marks and create an immutable-style audit event.

    The application does not let the LLM create valuations. Marks must come from an
    approved market/pricing source and are written through this controlled interface.
    """
    from app.models import AuditLog

    updated: list[int] = []
    details: list[str] = []
    for item in updates:
        trade = db.get(DerivativePosition, item.trade_id)
        if trade is None or trade.status != "OPEN":
            continue
        old = Decimal(trade.market_value_reporting_ccy)
        trade.market_value_reporting_ccy = Decimal(item.market_value_reporting_ccy)
        updated.append(trade.id)
        details.append(f"trade={trade.id}:{old}->{trade.market_value_reporting_ccy};source={item.source}")

    audit = AuditLog(
        event_type="DERIVATIVE_MTM_UPDATE",
        actor=actor,
        details=" | ".join(details)[:1000] if details else "No eligible open trades updated",
    )
    db.add(audit)
    db.commit()
    db.refresh(audit)
    return updated, audit.id
