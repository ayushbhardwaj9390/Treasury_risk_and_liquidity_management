from __future__ import annotations

import math
from datetime import UTC, datetime
from decimal import Decimal

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import BankAccount, LegalEntity, MarketCurvePoint, VolatilityQuote
from app.schemas.treasury import (
    BankAccountRationalizationOut,
    BankAccountRationalizationRow,
    DigitalTwinOut,
    DigitalTwinScenarioRequest,
    IntegratedScenarioRequest,
    LiquidityTransferPricingOut,
    LiquidityTransferPricingRow,
    MarketRiskCurrencyRow,
    MarketRiskDistributionOut,
)
from app.services.advanced_intelligence import calculate_intraday_liquidity
from app.services.derivative_risk import calculate_hedge_coverage
from app.services.fx import FXConversionError, convert
from app.services.global_treasury import calculate_cash_mobility, calculate_collateral_liquidity, calculate_refinancing_risk
from app.services.institutional_risk import calculate_liquidity_at_risk
from app.services.integrated_scenario import calculate_integrated_scenario
from app.services.liquidity import calculate_global_liquidity

ZERO = Decimal("0")


def _q(value: Decimal | float, places: str = "0.01") -> Decimal:
    return Decimal(str(value)).quantize(Decimal(places))


def _annual_vol_for_currency(db: Session, currency: str, horizon_days: int) -> tuple[Decimal, str]:
    if currency == settings.group_reporting_currency:
        return ZERO, "REPORTING_CURRENCY"
    candidates = [f"{currency}/{settings.group_reporting_currency}", f"{settings.group_reporting_currency}/{currency}"]
    quotes = db.scalars(select(VolatilityQuote).where(VolatilityQuote.asset_class == "FX", VolatilityQuote.underlying.in_(candidates))).all()
    if quotes:
        quote = min(quotes, key=lambda x: abs(x.tenor_days - horizon_days))
        return Decimal(quote.volatility), "MARKET_VOL"
    # Explicit conservative proxy where demo market data is incomplete. Never presented as a live quote.
    return Decimal("0.12"), "POLICY_PROXY"


def calculate_market_risk_distribution(
    db: Session,
    horizon_days: int = 10,
    confidence: Decimal = Decimal("0.95"),
    simulations: int = 5000,
    seed: int = 42,
) -> MarketRiskDistributionOut:
    if not 1 <= horizon_days <= 252:
        raise ValueError("horizon_days must be between 1 and 252")
    if not Decimal("0.90") <= confidence < Decimal("1"):
        raise ValueError("confidence must be between 0.90 and 1.00")
    if not 1000 <= simulations <= 50000:
        raise ValueError("simulations must be between 1000 and 50000")

    exposures = []
    rows: list[MarketRiskCurrencyRow] = []
    warnings: list[str] = []
    z95 = 1.6448536269514722
    phi_z = math.exp(-0.5 * z95 * z95) / math.sqrt(2 * math.pi)
    es_factor = phi_z / 0.05

    for h in calculate_hedge_coverage(db):
        residual_local = Decimal(h.residual_exposure)
        if residual_local == ZERO:
            continue
        try:
            residual_reporting = convert(db, residual_local, h.currency, settings.group_reporting_currency)
        except FXConversionError as exc:
            warnings.append(str(exc))
            continue
        vol, status = _annual_vol_for_currency(db, h.currency, horizon_days)
        sigma_h = float(vol) * math.sqrt(horizon_days / 252)
        standalone_sigma = abs(float(residual_reporting)) * sigma_h
        standalone_var = standalone_sigma * z95
        standalone_es = standalone_sigma * es_factor
        exposures.append((h.currency, float(residual_reporting), float(vol)))
        rows.append(MarketRiskCurrencyRow(
            currency=h.currency,
            residual_exposure_local=residual_local,
            residual_exposure_reporting=_q(residual_reporting),
            annualized_volatility=vol,
            var_95=_q(standalone_var),
            expected_shortfall_95=_q(standalone_es),
            data_status=status,
        ))
        if status == "POLICY_PROXY":
            warnings.append(f"{h.currency}: live/approved FX volatility unavailable; 12% annual policy proxy used for risk measurement only.")

    risk_exposures = [(c, e, v) for c, e, v in exposures if v > 0]
    if not risk_exposures:
        return MarketRiskDistributionOut(
            reporting_currency=settings.group_reporting_currency,
            horizon_days=horizon_days,
            confidence=confidence,
            simulations=simulations,
            portfolio_var_95=ZERO,
            portfolio_expected_shortfall_95=ZERO,
            earnings_at_risk_95_90d=ZERO,
            rows=rows,
            methodology="Delta-normal Monte Carlo on residual FX exposures",
            warnings=warnings,
        )

    exp = np.array([x[1] for x in risk_exposures], dtype=float)
    vols = np.array([x[2] for x in risk_exposures], dtype=float)
    n = len(exp)
    corr = np.full((n, n), 0.25, dtype=float)
    np.fill_diagonal(corr, 1.0)
    rng = np.random.default_rng(seed)
    normals = rng.multivariate_normal(np.zeros(n), corr, size=simulations)

    scale_10d = vols * math.sqrt(horizon_days / 252)
    pnl = (normals * scale_10d * exp).sum(axis=1)
    losses = -pnl
    var = float(np.quantile(losses, float(confidence)))
    tail = losses[losses >= var]
    es = float(tail.mean()) if tail.size else var

    rng_ear = np.random.default_rng(seed + 101)
    normals_90 = rng_ear.multivariate_normal(np.zeros(n), corr, size=simulations)
    pnl_90 = (normals_90 * (vols * math.sqrt(90 / 252)) * exp).sum(axis=1)
    ear = float(np.quantile(-pnl_90, float(confidence)))

    warnings.append("Correlation is a transparent 25% cross-currency demo assumption until an approved historical correlation matrix is connected.")
    warnings.append("VaR/EaR are modelled risk estimates, not limits on possible loss or liquidity need.")
    return MarketRiskDistributionOut(
        reporting_currency=settings.group_reporting_currency,
        horizon_days=horizon_days,
        confidence=confidence,
        simulations=simulations,
        portfolio_var_95=_q(max(var, 0.0)),
        portfolio_expected_shortfall_95=_q(max(es, 0.0)),
        earnings_at_risk_95_90d=_q(max(ear, 0.0)),
        rows=rows,
        methodology="Seeded Monte Carlo on residual FX exposures with approved/proxy volatilities and explicit cross-currency correlation assumption",
        warnings=warnings,
    )


def calculate_liquidity_transfer_pricing(db: Session) -> LiquidityTransferPricingOut:
    liq = calculate_global_liquidity(db)
    points = db.scalars(select(MarketCurvePoint).where(
        MarketCurvePoint.currency == settings.group_reporting_currency,
        MarketCurvePoint.curve_type == "DISCOUNT",
    )).all()
    warnings: list[str] = []
    if points:
        benchmark_point = min(points, key=lambda x: abs(x.tenor_days - 90))
        benchmark = Decimal(benchmark_point.zero_rate)
    else:
        benchmark = Decimal("0.05")
        warnings.append("Approved reporting-currency curve unavailable; 5% policy benchmark proxy used.")
    surplus_rate = max(benchmark - Decimal("0.0025"), ZERO)
    deficit_rate = benchmark + Decimal("0.0100")
    rows: list[LiquidityTransferPricingRow] = []
    net_charge = ZERO
    for e in liq.entities:
        pos = Decimal(e.liquidity_headroom_reporting)
        if pos >= 0:
            rate = surplus_rate
            charge = -(pos * rate)
            kind = "SURPLUS"
        else:
            rate = deficit_rate
            charge = abs(pos) * rate
            kind = "DEFICIT"
        net_charge += charge
        rows.append(LiquidityTransferPricingRow(
            entity_id=e.entity_id,
            entity_name=e.entity_name,
            liquidity_position_reporting=_q(pos),
            position_type=kind,
            internal_rate=_q(rate, "0.000001"),
            annual_internal_charge_or_credit=_q(charge),
            status="MANAGEMENT_PRICING_ONLY",
        ))
    warnings.append("Liquidity transfer pricing is an internal management-allocation mechanism, not tax transfer-pricing advice or a legal intercompany interest rate.")
    return LiquidityTransferPricingOut(
        reporting_currency=settings.group_reporting_currency,
        benchmark_rate=_q(benchmark, "0.000001"),
        surplus_credit_rate=_q(surplus_rate, "0.000001"),
        deficit_charge_rate=_q(deficit_rate, "0.000001"),
        net_internal_charge=_q(net_charge),
        rows=rows,
        methodology="90-day reporting-currency curve benchmark with transparent internal surplus/deficit liquidity spreads",
        warnings=warnings,
    )


def calculate_bank_account_rationalization(db: Session) -> BankAccountRationalizationOut:
    entities = {x.id: x for x in db.scalars(select(LegalEntity)).all()}
    accounts = db.scalars(select(BankAccount).order_by(BankAccount.bank_name, BankAccount.id)).all()
    now = datetime.now(UTC).replace(tzinfo=None)
    rows: list[BankAccountRationalizationRow] = []
    bank_totals: dict[str, Decimal] = {}
    total = ZERO
    stale = 0
    review = 0
    warnings: list[str] = []

    for a in accounts:
        gross = Decimal(a.book_balance)
        restricted = Decimal(a.restricted_balance)
        committed = Decimal(a.committed_outflows)
        deployable_local = max(gross - restricted - committed, ZERO)
        try:
            deployable_reporting = convert(db, deployable_local, a.currency, settings.group_reporting_currency)
        except FXConversionError:
            deployable_reporting = ZERO
            warnings.append(f"Account {a.id}: FX conversion unavailable; balance excluded from bank concentration totals.")
        age_hours = max(int((now - a.last_updated).total_seconds() // 3600), 0)
        restricted_ratio = (restricted / gross) if gross > 0 else ZERO
        is_pool = "POOL" in a.bank_name.upper() or "POOL" in a.account_type.upper()
        if age_hours > 24:
            stale += 1
        if is_pool:
            role = "POOL_INFRASTRUCTURE"
            recommendation = "RETAIN"
            rationale = "Account is part of configured pooling infrastructure."
        elif deployable_reporting < Decimal("1000000") and restricted_ratio < Decimal("0.50"):
            role = "LOW_UTILIZATION"
            recommendation = "REVIEW_FOR_RATIONALIZATION"
            rationale = "Low deployable balance and no pooling role; review operational necessity, fees and local constraints."
            review += 1
        elif restricted_ratio >= Decimal("0.50"):
            role = "RESTRICTED_CASH"
            recommendation = "RETAIN_REVIEW_RESTRICTION"
            rationale = "High restricted-cash ratio; closure should not be proposed until legal/operational restriction is resolved."
        else:
            role = "OPERATING"
            recommendation = "RETAIN"
            rationale = "Material operating liquidity or active local banking role."
        if age_hours > 24:
            recommendation = "DATA_REVIEW" if recommendation == "RETAIN" else recommendation
            rationale += " Balance is stale beyond 24 hours."
        total += deployable_reporting
        bank_totals[a.bank_name] = bank_totals.get(a.bank_name, ZERO) + deployable_reporting
        rows.append(BankAccountRationalizationRow(
            account_id=a.id,
            entity_name=entities[a.entity_id].name,
            bank_name=a.bank_name,
            country_code=a.country_code,
            currency=a.currency,
            deployable_balance_reporting=_q(deployable_reporting),
            restricted_ratio=_q(restricted_ratio, "0.000001"),
            age_hours=age_hours,
            role=role,
            recommendation=recommendation,
            rationale=rationale,
        ))
    largest_bank = max(bank_totals, key=bank_totals.get) if bank_totals else None
    largest_share = (bank_totals[largest_bank] / total) if largest_bank and total > 0 else ZERO
    if largest_share > Decimal("0.35"):
        warnings.append(f"{largest_bank} holds more than 35% of modeled deployable bank cash; concentration review recommended.")
    return BankAccountRationalizationOut(
        reporting_currency=settings.group_reporting_currency,
        account_count=len(accounts),
        bank_count=len(bank_totals),
        stale_account_count=stale,
        review_candidate_count=review,
        largest_bank=largest_bank,
        largest_bank_share=_q(largest_share, "0.000001"),
        rows=rows,
        warnings=warnings,
    )


def run_digital_twin(db: Session, request: DigitalTwinScenarioRequest | None = None) -> DigitalTwinOut:
    from app.services.mvp11_risk import (
        calculate_historical_market_risk,
        calculate_xva_style_adjustments,
        calculate_liquidity_survival_horizon,
        calculate_funding_concentration,
        evaluate_treasury_risk_limits,
    )
    req = request or DigitalTwinScenarioRequest()
    liq = calculate_global_liquidity(db)
    scenario_req = IntegratedScenarioRequest(**req.model_dump())
    scenario = calculate_integrated_scenario(db, scenario_req)
    lar = calculate_liquidity_at_risk(db, horizon_weeks=req.weeks, confidence=Decimal("0.95"), simulations=2500, seed=42)
    intraday = calculate_intraday_liquidity(db)
    mobility = calculate_cash_mobility(db)
    collateral = calculate_collateral_liquidity(db)
    refi = calculate_refinancing_risk(db)
    historical_market = calculate_historical_market_risk(db)
    xva = calculate_xva_style_adjustments(db)
    survival = calculate_liquidity_survival_horizon(db)
    funding_concentration = calculate_funding_concentration(db)
    limits = evaluate_treasury_risk_limits(db, lar_simulations=500)

    stressed = Decimal(scenario.stressed_liquidity_headroom_after_overlays)
    breach_prob = Decimal(lar.probability_of_buffer_breach)
    intraday_need = Decimal(intraday.peak_intraday_funding_need)
    if stressed < 0 or breach_prob >= Decimal("0.10"):
        state = "STRESSED"
    elif breach_prob >= Decimal("0.05") or intraday_need > 0 or scenario.status == "WATCH":
        state = "WATCH"
    else:
        state = "RESILIENT"

    actions: list[str] = []
    if stressed < 0:
        actions.append(f"Pre-fund or preserve at least {abs(stressed):,.0f} {settings.group_reporting_currency} of scenario liquidity before the modeled breach.")
    if intraday_need > 0:
        actions.append(f"Maintain intraday committed liquidity of at least {intraday_need:,.0f} {settings.group_reporting_currency} for the modeled payment peak.")
    if Decimal(mobility.total_trapped_cash) > 0:
        actions.append("Review trapped-cash release options separately from headline group cash; do not assume immediate transferability.")
    if Decimal(collateral.stressed_margin_call) > Decimal(collateral.current_margin_call):
        actions.append("Reserve collateral liquidity for stressed margin calls before allocating surplus cash to discretionary uses.")
    if not actions:
        actions.append("Maintain current buffers and monitor forecast, market and counterparty triggers.")

    warnings = list(dict.fromkeys([*liq.warnings, *lar.warnings, *historical_market.warnings, *xva.warnings, *funding_concentration.warnings, *limits.warnings]))
    return DigitalTwinOut(
        twin_version="MVP-10.0",
        reporting_currency=settings.group_reporting_currency,
        state=state,
        base_liquidity_headroom=Decimal(liq.liquidity_headroom),
        scenario_stressed_headroom=stressed,
        first_buffer_breach_week=scenario.first_buffer_breach_week,
        liquidity_at_risk_95=Decimal(lar.liquidity_at_risk),
        cash_flow_at_risk_95=Decimal(lar.cash_flow_at_risk),
        buffer_breach_probability=breach_prob,
        market_var_95=Decimal(historical_market.portfolio_var),
        market_expected_shortfall_95=Decimal(historical_market.expected_shortfall),
        intraday_peak_funding_need=intraday_need,
        trapped_cash=Decimal(mobility.total_trapped_cash),
        stressed_collateral_call=Decimal(collateral.stressed_margin_call),
        debt_due_180d=Decimal(refi.debt_due_180d),
        historical_market_var_95=Decimal(historical_market.portfolio_var),
        xva_style_total=Decimal(xva.total_xva_style_adjustment),
        liquidity_survival_days=survival.survival_horizon_days,
        funding_top_lender_share=Decimal(funding_concentration.top_lender_share),
        treasury_limit_status=limits.overall_status,
        scenario=scenario,
        actions=actions,
        assumptions=[
            "Digital twin is a decision-support model, not a legal representation of cash mobility or an execution system.",
            "Market VaR uses residual FX exposure after mapped hedges; USD group-reporting exposure has no group FX translation shock.",
            "Stress, LaR, market-risk and intraday engines remain separate to avoid silent double counting.",
            "MVP-11 historical market calibration, XVA-style sensitivity, survival horizon, funding concentration and treasury limits are additive governed views and do not override base liquidity calculations.",
        ],
        warnings=warnings,
    )
