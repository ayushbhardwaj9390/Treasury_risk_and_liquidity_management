from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from math import sqrt

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import MarketReturnObservation
from app.schemas.treasury import (
    HedgeOptimizationRequest,
    LiquidityBufferComponent,
    OptimalLiquidityBufferOut,
    StrategicTreasuryOption,
    StrategicTreasuryPlanOut,
    StrategicTreasuryRequest,
    TreasuryRiskRadarOut,
    TreasuryRiskRadarScenario,
    TreasuryRiskRegimeFactor,
    IntegratedScenarioRequest,
)
from app.services.advanced_intelligence import calculate_intraday_liquidity
from app.services.digital_twin import calculate_bank_account_rationalization
from app.services.global_treasury import calculate_collateral_liquidity, calculate_refinancing_risk
from app.services.institutional_risk import calculate_liquidity_at_risk
from app.services.integrated_scenario import calculate_integrated_scenario
from app.services.liquidity import calculate_global_liquidity
from app.services.mvp11_risk import calculate_funding_concentration, calculate_liquidity_survival_horizon
from app.services.mvp12_liquidity_command import calculate_early_warning_indicators, calculate_interest_rate_gap_dv01, optimize_funding_tenor
from app.services.mvp14_forecast_working_capital import calculate_forecast_bias
from app.services.treasury_optimization import optimize_fx_hedges, optimize_funding

ZERO = Decimal("0")
ONE = Decimal("1")


def _q(value: Decimal | float | int, places: str = "0.01") -> Decimal:
    return Decimal(str(value)).quantize(Decimal(places))


def _clip(value: Decimal, lo: Decimal = ZERO, hi: Decimal = ONE) -> Decimal:
    return min(max(value, lo), hi)


def _market_regime(db: Session) -> tuple[str, Decimal, list[TreasuryRiskRegimeFactor], list[str]]:
    rows = db.scalars(
        select(MarketReturnObservation)
        .where(MarketReturnObservation.factor_type == "FX", MarketReturnObservation.approved.is_(True))
        .order_by(MarketReturnObservation.observation_date)
    ).all()
    by_factor: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        by_factor[row.factor_key].append(float(row.return_value))

    factors: list[TreasuryRiskRegimeFactor] = []
    warnings: list[str] = []
    ratios: list[float] = []
    for key, values in sorted(by_factor.items()):
        if len(values) < 40:
            continue
        recent = np.asarray(values[-20:], dtype=float)
        prior = np.asarray(values[-80:-20] if len(values) >= 80 else values[:-20], dtype=float)
        if len(prior) < 20:
            continue
        recent_vol = float(np.std(recent, ddof=1) * sqrt(252))
        prior_vol = float(np.std(prior, ddof=1) * sqrt(252))
        ratio = recent_vol / prior_vol if prior_vol > 1e-12 else 1.0
        ratios.append(ratio)
        regime = "STRESS" if ratio >= 1.75 else "ELEVATED" if ratio >= 1.30 else "CALM" if ratio <= 0.75 else "NORMAL"
        factors.append(TreasuryRiskRegimeFactor(
            factor_key=key,
            recent_volatility=_q(recent_vol, "0.000001"),
            prior_volatility=_q(prior_vol, "0.000001"),
            volatility_ratio=_q(ratio, "0.0001"),
            regime=regime,
        ))
    if not ratios:
        warnings.append("Insufficient approved historical observations for dynamic market-regime classification.")
        return "UNKNOWN", ZERO, factors, warnings
    avg = float(np.mean(ratios))
    regime = "STRESS" if avg >= 1.75 else "ELEVATED" if avg >= 1.30 else "CALM" if avg <= 0.75 else "NORMAL"
    confidence = min(1.0, len(factors) / 4.0) * min(1.0, max(len(v) for v in by_factor.values()) / 120.0)
    return regime, _q(confidence, "0.0001"), factors, warnings


def calculate_treasury_risk_radar(db: Session, horizon_days: int = 90) -> TreasuryRiskRadarOut:
    if not 30 <= horizon_days <= 365:
        raise ValueError("horizon_days must be between 30 and 365")
    ewi = calculate_early_warning_indicators(db)
    lar = calculate_liquidity_at_risk(db, simulations=1500, seed=42)
    survival = calculate_liquidity_survival_horizon(db, weeks=max(13, int(np.ceil(horizon_days / 7))))
    funding = calculate_funding_concentration(db)
    bias = calculate_forecast_bias(db, min(max(horizon_days * 2, 90), 365))
    regime, regime_confidence, regime_factors, regime_warnings = _market_regime(db)

    breach_p = Decimal(lar.probability_of_buffer_breach)
    survival_penalty = _clip((Decimal("84") - Decimal(survival.survival_horizon_days)) / Decimal("84"))
    lender_penalty = _clip((Decimal(funding.top_lender_share) - Decimal("0.25")) / Decimal("0.35"))
    cash_bias = max((Decimal(x.cash_bias_pct) for x in bias.rows), default=ZERO)
    bias_penalty = _clip(max(cash_bias, ZERO) / Decimal("0.15"))
    regime_penalty = {"CALM": Decimal("0.05"), "NORMAL": Decimal("0.20"), "ELEVATED": Decimal("0.55"), "STRESS": Decimal("0.90"), "UNKNOWN": Decimal("0.35")}[regime]
    ewi_penalty = _clip((Decimal(ewi.red_count) * Decimal("0.20") + Decimal(ewi.amber_count) * Decimal("0.08")))
    deterioration = _clip(
        breach_p * Decimal("0.30")
        + survival_penalty * Decimal("0.20")
        + lender_penalty * Decimal("0.12")
        + bias_penalty * Decimal("0.10")
        + regime_penalty * Decimal("0.18")
        + ewi_penalty * Decimal("0.10")
    )

    if deterioration >= Decimal("0.70"):
        overall = "RED"
    elif deterioration >= Decimal("0.40"):
        overall = "AMBER"
    else:
        overall = "GREEN"

    if regime == "STRESS":
        fx, rate = Decimal("0.15"), 300
    elif regime == "ELEVATED":
        fx, rate = Decimal("0.10"), 200
    else:
        fx, rate = Decimal("0.07"), 125
    scenarios_cfg = [
        ("RADAR_BASE", "Current-risk regime continuation", Decimal("0.90"), Decimal("1.05"), Decimal("0.90"), fx / 2, max(rate // 2, 50)),
        ("RADAR_DOWNSIDE", "Collections weaken and market/funding conditions tighten", Decimal("0.78"), Decimal("1.12"), Decimal("0.70"), fx, rate),
        ("RADAR_COMBINED", "Combined liquidity and market deterioration", Decimal("0.65"), Decimal("1.20"), Decimal("0.50"), min(fx * 2, Decimal("0.30")), min(rate * 2, 600)),
    ]
    scenarios: list[TreasuryRiskRadarScenario] = []
    for code, desc, rec, pay, fac, fx_s, rate_s in scenarios_cfg:
        result = calculate_integrated_scenario(db, IntegratedScenarioRequest(
            label=desc, weeks=13, receivable_multiplier=rec, payable_multiplier=pay,
            facility_availability=fac, fx_shock_pct=fx_s, rate_shock_bps=rate_s,
            collateral_stress_multiplier=Decimal("1.00"), refinancing_spread_shock_bps=rate_s,
        ))
        headroom = Decimal(result.stressed_liquidity_headroom_after_overlays)
        scenarios.append(TreasuryRiskRadarScenario(
            scenario_code=code, description=desc, receivable_multiplier=rec,
            payable_multiplier=pay, facility_availability=fac, fx_shock_pct=fx_s,
            rate_shock_bps=rate_s, stressed_headroom=_q(headroom),
            first_buffer_breach_week=result.first_buffer_breach_week,
            status="BREACH" if headroom < 0 else "WATCH" if result.first_buffer_breach_week else "RESILIENT",
        ))

    drivers: list[tuple[Decimal, str]] = [
        (breach_p, f"13-week modeled buffer-breach probability is {breach_p:.1%}."),
        (survival_penalty, f"Liquidity survival horizon is {survival.survival_horizon_days} days."),
        (lender_penalty, f"Top funding provider represents {Decimal(funding.top_lender_share):.1%} of modeled funding capacity."),
        (regime_penalty, f"Historical FX regime is classified {regime}."),
        (bias_penalty, f"Largest entity forecast cash bias is {cash_bias:.1%}."),
    ]
    primary = [text for _, text in sorted(drivers, key=lambda x: x[0], reverse=True)[:4]]
    return TreasuryRiskRadarOut(
        reporting_currency=settings.group_reporting_currency,
        horizon_days=horizon_days,
        overall_status=overall,
        deterioration_score=_q(deterioration, "0.0001"),
        liquidity_breach_probability=_q(breach_p, "0.000001"),
        survival_horizon_days=survival.survival_horizon_days,
        market_regime=regime,
        regime_confidence=regime_confidence,
        top_lender_share=_q(funding.top_lender_share, "0.0001"),
        forecast_cash_bias_pct=_q(cash_bias, "0.0001"),
        regime_factors=regime_factors,
        dynamic_scenarios=scenarios,
        primary_drivers=primary,
        execution_authority="NONE",
        warnings=[
            *regime_warnings,
            "Deterioration score is a governed composite indicator, not a calibrated probability of loss or default.",
            "Only the Monte Carlo liquidity engine reports modeled buffer-breach probability; dynamic radar scenarios are deterministic stresses.",
        ],
    )


def calculate_optimal_liquidity_buffer(db: Session) -> OptimalLiquidityBufferOut:
    liq = calculate_global_liquidity(db)
    lar = calculate_liquidity_at_risk(db, simulations=2500, seed=42)
    intraday = calculate_intraday_liquidity(db)
    collateral = calculate_collateral_liquidity(db)
    refi = calculate_refinancing_risk(db)

    operating = Decimal(liq.minimum_cash)
    tail = max(Decimal(lar.tail_funding_need), ZERO)
    intraday_need = max(Decimal(intraday.peak_intraday_funding_need), ZERO)
    incremental_collateral = max(Decimal(collateral.stressed_margin_call) - Decimal(collateral.current_margin_call), ZERO)
    refinancing_reserve = max(Decimal(refi.debt_due_180d) * Decimal("0.05"), ZERO)

    # Lower bound avoids double counting concurrent short-horizon calls; upper bound is deliberately conservative.
    short_term_overlay = max(intraday_need, incremental_collateral)
    lower = max(operating, tail) + short_term_overlay
    upper = operating + tail + intraday_need + incremental_collateral + refinancing_reserve
    recommended = lower + (upper - lower) * Decimal("0.50")
    components = [
        LiquidityBufferComponent(component="OPERATING_MINIMUM", amount_reporting=_q(operating), treatment="BASE", rationale="Legal-entity/group minimum operating liquidity."),
        LiquidityBufferComponent(component="TAIL_LIQUIDITY", amount_reporting=_q(tail), treatment="PRIMARY_STRESS", rationale="Modeled tail funding need from the liquidity-at-risk engine."),
        LiquidityBufferComponent(component="INTRADAY", amount_reporting=_q(intraday_need), treatment="SHORT_HORIZON_OVERLAY", rationale="Peak modeled intraday funding need."),
        LiquidityBufferComponent(component="COLLATERAL", amount_reporting=_q(incremental_collateral), treatment="SHORT_HORIZON_OVERLAY", rationale="Incremental stressed collateral call above current margin."),
        LiquidityBufferComponent(component="REFINANCING", amount_reporting=_q(refinancing_reserve), treatment="STRATEGIC_RESERVE", rationale="5% planning reserve against debt due within 180 days; replace with approved refinancing policy."),
    ]
    return OptimalLiquidityBufferOut(
        reporting_currency=settings.group_reporting_currency,
        current_minimum_cash=_q(operating), lower_buffer_bound=_q(lower), recommended_buffer=_q(recommended),
        upper_buffer_bound=_q(upper), current_deployable_cash=_q(liq.deployable_cash),
        buffer_surplus_or_gap=_q(Decimal(liq.deployable_cash) - recommended), components=components,
        methodology="Operating floor plus LaR tail need with non-double-counted short-horizon intraday/collateral overlay and an explicit refinancing planning reserve.",
        execution_authority="NONE",
        warnings=[
            "Recommended buffer is a treasury planning range, not a regulatory liquidity requirement.",
            "Intraday and collateral demands may overlap; the lower bound uses the larger short-horizon call rather than summing both.",
            "Company risk appetite, committed-facility legal certainty and rating objectives must calibrate the final buffer.",
        ],
    )


def optimize_strategic_treasury(db: Session, request: StrategicTreasuryRequest | None = None) -> StrategicTreasuryPlanOut:
    req = request or StrategicTreasuryRequest()
    if not 1 <= req.horizon_years <= 7:
        raise ValueError("horizon_years must be between 1 and 7")
    objective = req.objective.upper()
    buffer = calculate_optimal_liquidity_buffer(db)
    rates = calculate_interest_rate_gap_dv01(db)
    funding_conc = calculate_funding_concentration(db)
    tenor = optimize_funding_tenor(db, req.incremental_funding_need)
    bank = calculate_bank_account_rationalization(db)
    lar = calculate_liquidity_at_risk(db, simulations=1500, seed=42)
    total_debt = Decimal(rates.fixed_debt_reporting) + Decimal(rates.floating_debt_reporting)
    fixed_share = Decimal(rates.fixed_debt_reporting) / total_debt if total_debt > 0 else ZERO

    profiles = [
        ("LIQUIDITY_RESILIENCE", "Prioritize liquidity and refinancing resilience.", Decimal("0.70"), Decimal("0.70"), Decimal("0.30"), Decimal("0.60")),
        ("BALANCED", "Balance funding stability, hedge coverage and liquidity cost.", Decimal("0.65"), Decimal("0.75"), Decimal("0.35"), Decimal("0.50")),
        ("RISK_STABILITY", "Reduce rate/FX variability with higher fixed-rate and hedge targets.", Decimal("0.80"), Decimal("0.85"), Decimal("0.30"), Decimal("0.65")),
    ]
    strategies: list[StrategicTreasuryOption] = []
    tail_need = Decimal(lar.tail_funding_need)
    for code, desc, target_fixed, hedge_ratio, lender_target, long_term_share in profiles:
        hedge = optimize_fx_hedges(db, HedgeOptimizationRequest(target_hedge_ratio=hedge_ratio, option_share=Decimal("0.25")))
        requested = Decimal(req.incremental_funding_need) if req.incremental_funding_need is not None else max(tail_need, ZERO)
        funding = optimize_funding(db, requested, Decimal("0.50"))
        rate_sens = max(ONE - target_fixed, ZERO) * total_debt * Decimal("0.01")
        lender_excess = max(Decimal(funding_conc.top_lender_share) - lender_target, ZERO)
        residual_tail = Decimal(funding.uncovered_funding)
        buffer_gap = max(Decimal(buffer.recommended_buffer) - Decimal(buffer.current_deployable_cash), ZERO)
        resilience = Decimal("100") - min(Decimal("45"), residual_tail / max(requested, ONE) * Decimal("45")) - min(Decimal("20"), lender_excess * Decimal("100")) - min(Decimal("20"), rate_sens / max(total_debt, ONE) * Decimal("2000")) - min(Decimal("15"), buffer_gap / max(Decimal(buffer.recommended_buffer), ONE) * Decimal("15"))
        status = "REVIEW" if residual_tail > 0 or lender_excess > 0 else "FEASIBLE"
        strategies.append(StrategicTreasuryOption(
            strategy_code=code, description=desc, target_fixed_rate_share=target_fixed,
            target_fx_hedge_ratio=hedge_ratio, target_top_lender_share=lender_target,
            target_long_term_funding_share=long_term_share, liquidity_buffer_target=Decimal(buffer.recommended_buffer),
            incremental_hedge_reporting=Decimal(hedge.total_incremental_hedge_reporting),
            modeled_tail_funding_need=_q(tail_need), residual_unfunded_tail=_q(residual_tail),
            rate_cash_sensitivity_100bps=_q(rate_sens), funding_concentration_status="REVIEW" if lender_excess > 0 else "WITHIN_TARGET",
            resilience_score=_q(max(resilience, ZERO), "0.01"), cost_data_completeness="INCOMPLETE_EXECUTABLE_PRICING",
            status=status,
        ))

    valid = {x.strategy_code for x in strategies}
    selected = objective if objective in valid else "BALANCED"
    actions = [
        f"Maintain a treasury liquidity planning buffer around {Decimal(buffer.recommended_buffer):,.0f} {settings.group_reporting_currency}, subject to approved risk appetite.",
        f"Use the funding-tenor plan to reduce near-term refinancing concentration; current top-lender share is {Decimal(funding_conc.top_lender_share):.1%}.",
        f"Current fixed-rate debt share is {fixed_share:.1%}; compare target structure against executable swap/debt pricing before approval.",
        f"Review {bank.review_candidate_count} bank-account rationalization candidates without compromising local operating or pooling requirements.",
        "Route strategic hedge changes only against residual business exposures and within treasury policy bands.",
    ]
    return StrategicTreasuryPlanOut(
        reporting_currency=settings.group_reporting_currency, horizon_years=req.horizon_years,
        objective=objective, selected_strategy_code=selected,
        current_fixed_rate_share=_q(fixed_share, "0.0001"), current_top_lender_share=_q(funding_conc.top_lender_share, "0.0001"),
        optimal_liquidity_buffer=buffer, strategies=strategies, strategic_actions=actions,
        human_approval_required=True, execution_authority="NONE",
        warnings=[
            "Strategic optimization compares resilience structures, not predicted market direction.",
            "Executable debt spreads, fees, FX basis, option premia, tax effects, ratings impact and legal capacity remain mandatory before implementation.",
            "No strategy can create, approve or execute a treasury transaction.",
            f"Funding-tenor optimizer currently proposes {len(tenor.rows)} maturity buckets; these remain non-executable planning targets.",
        ],
    )
