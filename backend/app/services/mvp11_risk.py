from __future__ import annotations

import math
from collections import defaultdict
from datetime import date
from decimal import Decimal
from statistics import NormalDist

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import (
    CounterpartyCreditMetric,
    CreditFacility,
    DebtPosition,
    DerivativePosition,
    LegalNettingSet,
    MarketReturnObservation,
    NettingSetTrade,
    TreasuryRiskLimit,
)
from app.schemas.treasury import (
    DigitalTwinOptimizationOut,
    DigitalTwinOptimizationRequest,
    DigitalTwinOptimizedScenario,
    FundingConcentrationOut,
    FundingConcentrationRow,
    HistoricalCorrelationPair,
    HistoricalFactorStat,
    HistoricalMarketCalibrationOut,
    HistoricalMarketRiskOut,
    IntegratedScenarioRequest,
    LiquiditySurvivalOut,
    TreasuryRiskLimitFrameworkOut,
    TreasuryRiskLimitStatus,
    XVAExposureRow,
    XVAOut,
)
from app.services.derivative_risk import calculate_counterparty_exposure, calculate_hedge_coverage
from app.services.forecast import calculate_custom_liquidity_forecast
from app.services.fx import FXConversionError, convert
from app.services.institutional_risk import calculate_legal_netting, calculate_liquidity_at_risk
from app.services.integrated_scenario import calculate_integrated_scenario
from app.services.liquidity import calculate_global_liquidity

ZERO = Decimal("0")
ONE = Decimal("1")


def _q(value: Decimal | float, places: str = "0.01") -> Decimal:
    return Decimal(str(value)).quantize(Decimal(places))


def calculate_historical_market_calibration(
    db: Session,
    lookback_observations: int = 120,
    ewma_lambda: Decimal = Decimal("0.94"),
) -> HistoricalMarketCalibrationOut:
    if not 40 <= lookback_observations <= 750:
        raise ValueError("lookback_observations must be between 40 and 750")
    lam = float(ewma_lambda)
    if not 0.80 <= lam < 1.0:
        raise ValueError("ewma_lambda must be between 0.80 and 1.00")

    rows = db.scalars(
        select(MarketReturnObservation)
        .where(MarketReturnObservation.factor_type == "FX", MarketReturnObservation.approved.is_(True))
        .order_by(MarketReturnObservation.observation_date)
    ).all()
    by_date: dict[date, dict[str, float]] = defaultdict(dict)
    source_set: set[str] = set()
    for row in rows:
        by_date[row.observation_date][row.factor_key] = float(row.return_value)
        source_set.add(row.source)
    dates = sorted(by_date)[-lookback_observations:]
    factors = sorted({f for d in dates for f in by_date[d]})
    warnings: list[str] = []
    if len(dates) < 60:
        warnings.append("Historical market sample is shorter than 60 observations; correlation stability is limited.")
    if len(factors) < 2:
        warnings.append("Fewer than two approved FX factors are available; portfolio correlation cannot be estimated robustly.")

    complete_dates = [d for d in dates if all(f in by_date[d] for f in factors)]
    if not complete_dates or not factors:
        return HistoricalMarketCalibrationOut(
            lookback_observations=0,
            ewma_lambda=Decimal(str(ewma_lambda)),
            factors=[], correlations=[], source_status="INSUFFICIENT_DATA",
            warnings=[*warnings, "No complete approved historical return matrix is available."],
        )

    matrix = np.array([[by_date[d][f] for f in factors] for d in complete_dates], dtype=float)
    n = matrix.shape[0]
    raw_vol = matrix.std(axis=0, ddof=1) * math.sqrt(252) if n > 1 else np.zeros(len(factors))
    weights = np.array([(1.0 - lam) * (lam ** (n - 1 - i)) for i in range(n)], dtype=float)
    weights /= weights.sum()
    mean = np.average(matrix, axis=0, weights=weights)
    centered = matrix - mean
    cov_daily = (centered * weights[:, None]).T @ centered
    cov_annual = cov_daily * 252.0
    ewma_vol = np.sqrt(np.maximum(np.diag(cov_annual), 0.0))
    denom = np.outer(ewma_vol, ewma_vol)
    corr = np.divide(cov_annual, denom, out=np.eye(len(factors)), where=denom > 0)
    corr = np.clip(corr, -1.0, 1.0)

    factor_rows = [
        HistoricalFactorStat(
            factor_key=f,
            observations=n,
            annualized_volatility=_q(raw_vol[i], "0.000001"),
            ewma_volatility=_q(ewma_vol[i], "0.000001"),
            latest_return=_q(matrix[-1, i], "0.00000001"),
            data_status="APPROVED_HISTORY",
        )
        for i, f in enumerate(factors)
    ]
    pairs: list[HistoricalCorrelationPair] = []
    for i in range(len(factors)):
        for j in range(i + 1, len(factors)):
            pairs.append(HistoricalCorrelationPair(
                factor_a=factors[i], factor_b=factors[j], correlation=_q(corr[i, j], "0.000001")
            ))
    return HistoricalMarketCalibrationOut(
        lookback_observations=n,
        ewma_lambda=Decimal(str(ewma_lambda)),
        factors=factor_rows,
        correlations=pairs,
        source_status="APPROVED_HISTORY" if source_set else "INSUFFICIENT_DATA",
        warnings=warnings,
    )


def _historical_covariance(db: Session, lookback: int = 120, ewma_lambda: float = 0.94):
    rows = db.scalars(
        select(MarketReturnObservation)
        .where(MarketReturnObservation.factor_type == "FX", MarketReturnObservation.approved.is_(True))
        .order_by(MarketReturnObservation.observation_date)
    ).all()
    by_date: dict[date, dict[str, float]] = defaultdict(dict)
    for row in rows:
        by_date[row.observation_date][row.factor_key] = float(row.return_value)
    dates = sorted(by_date)[-lookback:]
    factors = sorted({f for d in dates for f in by_date[d]})
    complete = [d for d in dates if all(f in by_date[d] for f in factors)]
    if len(complete) < 40 or not factors:
        return [], np.zeros((0, 0)), 0
    matrix = np.array([[by_date[d][f] for f in factors] for d in complete], dtype=float)
    n = matrix.shape[0]
    weights = np.array([(1.0 - ewma_lambda) * (ewma_lambda ** (n - 1 - i)) for i in range(n)], dtype=float)
    weights /= weights.sum()
    mean = np.average(matrix, axis=0, weights=weights)
    centered = matrix - mean
    cov_daily = (centered * weights[:, None]).T @ centered
    return factors, cov_daily, n


def calculate_historical_market_risk(
    db: Session,
    horizon_days: int = 10,
    confidence: Decimal = Decimal("0.95"),
    lookback_observations: int = 120,
) -> HistoricalMarketRiskOut:
    if not 1 <= horizon_days <= 252:
        raise ValueError("horizon_days must be between 1 and 252")
    conf = float(confidence)
    if not 0.90 <= conf < 1.0:
        raise ValueError("confidence must be between 0.90 and 1.00")

    factors, cov_daily, obs = _historical_covariance(db, lookback_observations)
    warnings: list[str] = []
    exposures = {h.currency: h for h in calculate_hedge_coverage(db)}
    vector = np.zeros(len(factors), dtype=float)
    used = 0
    for i, factor in enumerate(factors):
        hedge = exposures.get(factor)
        if hedge is None:
            continue
        try:
            vector[i] = float(convert(db, Decimal(hedge.residual_exposure), factor, settings.group_reporting_currency))
            used += 1
        except FXConversionError as exc:
            warnings.append(str(exc))
    if used == 0 or not factors:
        return HistoricalMarketRiskOut(
            reporting_currency=settings.group_reporting_currency, horizon_days=horizon_days, confidence=confidence,
            portfolio_var=ZERO, expected_shortfall=ZERO, earnings_at_risk_90d=ZERO,
            correlation_method="INSUFFICIENT_HISTORY", factor_count=0,
            warnings=[*warnings, "No mapped residual FX exposure has approved historical factor data."],
        )

    variance_day = float(vector.T @ cov_daily @ vector)
    sigma_h = math.sqrt(max(variance_day, 0.0) * horizon_days)
    z = NormalDist().inv_cdf(conf)
    phi = math.exp(-0.5 * z * z) / math.sqrt(2 * math.pi)
    es_factor = phi / (1.0 - conf)
    var = sigma_h * z
    es = sigma_h * es_factor
    ear90 = math.sqrt(max(variance_day, 0.0) * 90.0) * z
    if obs < 100:
        warnings.append("Historical calibration uses fewer than 100 complete observations; use additional history before production limit setting.")
    warnings.append("Historical VaR/EaR uses EWMA covariance on approved residual FX factors and remains a model estimate, not a maximum-loss guarantee.")
    return HistoricalMarketRiskOut(
        reporting_currency=settings.group_reporting_currency,
        horizon_days=horizon_days,
        confidence=confidence,
        portfolio_var=_q(max(var, 0.0)),
        expected_shortfall=_q(max(es, 0.0)),
        earnings_at_risk_90d=_q(max(ear90, 0.0)),
        correlation_method=f"EWMA_{obs}_OBS_LAMBDA_0.94",
        factor_count=used,
        warnings=warnings,
    )


def calculate_xva_style_adjustments(db: Session) -> XVAOut:
    netting = calculate_legal_netting(db)
    metrics = {m.counterparty: m for m in db.scalars(select(CounterpartyCreditMetric)).all()}
    netting_sets = {n.netting_set_code: n for n in db.scalars(select(LegalNettingSet)).all()}
    links = db.scalars(select(NettingSetTrade)).all()
    trades = {t.id: t for t in db.scalars(select(DerivativePosition).where(DerivativePosition.status == "OPEN")).all()}
    set_trade_ids: dict[int, list[int]] = defaultdict(list)
    for link in links:
        set_trade_ids[link.netting_set_id].append(link.derivative_position_id)

    rows: list[XVAExposureRow] = []
    total_cva = ZERO
    total_fva = ZERO
    warnings: list[str] = []
    today = date.today()
    for n in netting.rows:
        metric = metrics.get(n.counterparty)
        ns = netting_sets.get(n.netting_set_code)
        if ns:
            maturities = [max((trades[tid].maturity_date - today).days, 1) / 365 for tid in set_trade_ids.get(ns.id, []) if tid in trades]
        else:
            maturities = []
        avg_years = sum(maturities) / len(maturities) if maturities else 1.0
        exposure = Decimal(n.exposure_after_netting_and_collateral)
        if metric and metric.approved:
            pd = Decimal(metric.one_year_pd)
            lgd = Decimal(metric.lgd)
            spread_bps = Decimal(metric.funding_spread_bps)
            status = "APPROVED_INPUTS"
        else:
            pd, lgd, spread_bps = Decimal("0.01"), Decimal("0.60"), Decimal("100")
            status = "REVIEW_REQUIRED"
            warnings.append(f"{n.counterparty}: approved credit metric unavailable; conservative policy proxy used for XVA-style sensitivity only.")
        horizon_pd = ONE - Decimal(str((1.0 - float(pd)) ** min(avg_years, 5.0)))
        discount = Decimal(str(math.exp(-0.05 * min(avg_years, 5.0))))
        cva = exposure * horizon_pd * lgd * discount
        # FVA-style: cost of funding net credit/collateral exposure over average remaining maturity.
        funding_base = exposure + Decimal(n.collateral_posted)
        fva = funding_base * (spread_bps / Decimal("10000")) * Decimal(str(min(avg_years, 5.0))) * discount
        total_cva += cva
        total_fva += fva
        rows.append(XVAExposureRow(
            counterparty=n.counterparty,
            netting_set_code=n.netting_set_code,
            exposure_after_netting_collateral=_q(exposure),
            one_year_pd=_q(pd, "0.000001"), lgd=_q(lgd, "0.000001"), funding_spread_bps=_q(spread_bps, "0.01"),
            average_maturity_years=_q(avg_years, "0.0001"),
            cva_style_adjustment=_q(cva), fva_style_adjustment=_q(fva), total_xva_style_adjustment=_q(cva + fva),
            data_status=status,
        ))
    warnings.append("CVA/FVA outputs are treasury risk sensitivities, not accounting fair-value adjustments; production XVA requires approved exposure profiles, credit curves, funding curves and independent model validation.")
    return XVAOut(
        reporting_currency=settings.group_reporting_currency,
        cva_style_total=_q(total_cva), fva_style_total=_q(total_fva), total_xva_style_adjustment=_q(total_cva + total_fva),
        rows=rows, methodology="Netting-set exposure × horizon PD × LGD plus simplified funding-spread carry", warnings=list(dict.fromkeys(warnings)),
    )


def calculate_liquidity_survival_horizon(
    db: Session,
    weeks: int = 26,
    receivable_multiplier: Decimal = Decimal("0.60"),
    payable_multiplier: Decimal = Decimal("1.20"),
    facility_availability: Decimal = Decimal("0.50"),
) -> LiquiditySurvivalOut:
    if not 1 <= weeks <= 52:
        raise ValueError("weeks must be between 1 and 52")
    liq = calculate_global_liquidity(db)
    forecast = calculate_custom_liquidity_forecast(db, receivable_multiplier, payable_multiplier, facility_availability, weeks, "Liquidity survival stress")
    min_effective = None
    hard_depletion_week = None
    for p in forecast.points:
        effective = Decimal(p.closing_cash) + Decimal(p.available_facility)
        min_effective = effective if min_effective is None else min(min_effective, effective)
        if effective <= 0 and hard_depletion_week is None:
            hard_depletion_week = p.week
    first_breach = forecast.first_buffer_breach_week
    survival_days = weeks * 7 if first_breach is None else max((first_breach - 1) * 7, 0)
    status = "CRITICAL" if hard_depletion_week is not None else "BREACH" if first_breach is not None else "SURVIVES_HORIZON"
    warnings = list(forecast.warnings)
    if first_breach is None:
        warnings.append(f"Minimum liquidity buffer survives the {weeks}-week configured stress horizon; this does not imply unlimited survival beyond the horizon.")
    return LiquiditySurvivalOut(
        reporting_currency=settings.group_reporting_currency,
        horizon_weeks=weeks,
        scenario_label="60% collections / 120% payables / 50% facility availability",
        starting_deployable_cash=Decimal(liq.deployable_cash),
        starting_available_facilities=Decimal(liq.undrawn_credit) * facility_availability,
        minimum_liquidity_buffer=Decimal(liq.minimum_cash),
        first_buffer_breach_week=first_breach,
        first_buffer_breach_day_estimate=(first_breach - 1) * 7 if first_breach else None,
        hard_liquidity_depletion_week=hard_depletion_week,
        survival_horizon_days=survival_days,
        ending_effective_liquidity=_q(Decimal(forecast.ending_cash) + (Decimal(liq.undrawn_credit) * facility_availability)),
        minimum_effective_liquidity=_q(min_effective or ZERO),
        status=status,
        warnings=warnings,
    )


def calculate_funding_concentration(db: Session) -> FundingConcentrationOut:
    by_lender: dict[str, dict[str, Decimal]] = defaultdict(lambda: {"debt": ZERO, "facility": ZERO, "undrawn": ZERO, "due180": ZERO})
    warnings: list[str] = []
    today = date.today()
    for debt in db.scalars(select(DebtPosition).where(DebtPosition.status == "OPEN")).all():
        try:
            amount = abs(convert(db, Decimal(debt.principal), debt.currency, settings.group_reporting_currency))
        except FXConversionError as exc:
            warnings.append(str(exc)); continue
        by_lender[debt.lender]["debt"] += amount
        if (debt.maturity_date - today).days <= 180:
            by_lender[debt.lender]["due180"] += amount
    for fac in db.scalars(select(CreditFacility).where(CreditFacility.committed.is_(True))).all():
        try:
            limit = abs(convert(db, Decimal(fac.limit_amount), fac.currency, settings.group_reporting_currency))
            undrawn = abs(convert(db, max(Decimal(fac.limit_amount) - Decimal(fac.drawn_amount), ZERO), fac.currency, settings.group_reporting_currency))
        except FXConversionError as exc:
            warnings.append(str(exc)); continue
        by_lender[fac.lender]["facility"] += limit
        by_lender[fac.lender]["undrawn"] += undrawn
        if fac.maturity_date and (fac.maturity_date - today).days <= 180:
            by_lender[fac.lender]["due180"] += undrawn
    totals = {l: v["debt"] + v["facility"] for l, v in by_lender.items()}
    total = sum(totals.values(), ZERO)
    rows: list[FundingConcentrationRow] = []
    for lender, values in sorted(by_lender.items(), key=lambda kv: totals[kv[0]], reverse=True):
        share = totals[lender] / total if total > 0 else ZERO
        rows.append(FundingConcentrationRow(
            lender=lender, debt_reporting=_q(values["debt"]), committed_facility_reporting=_q(values["facility"]),
            undrawn_facility_reporting=_q(values["undrawn"]), total_funding_capacity_reporting=_q(totals[lender]),
            share_of_total_funding=_q(share, "0.000001"), maturity_within_180d_reporting=_q(values["due180"]),
        ))
    shares = [Decimal(r.share_of_total_funding) for r in rows]
    top1 = shares[0] if shares else ZERO
    top3 = sum(shares[:3], ZERO)
    hhi = sum((x * x for x in shares), ZERO)
    due180 = sum((Decimal(r.maturity_within_180d_reporting) for r in rows), ZERO)
    if top1 > Decimal("0.40"):
        warnings.append("Largest funding provider exceeds 40% of modeled debt plus committed facility capacity.")
    if hhi > Decimal("0.25"):
        warnings.append("Funding-provider HHI exceeds 0.25, indicating elevated concentration in the modeled funding stack.")
    return FundingConcentrationOut(
        reporting_currency=settings.group_reporting_currency, total_funding_reporting=_q(total), lender_count=len(rows),
        top_lender=rows[0].lender if rows else None, top_lender_share=_q(top1, "0.000001"), top_three_share=_q(top3, "0.000001"),
        hhi=_q(hhi, "0.000001"), funding_due_180d=_q(due180), rows=rows, warnings=warnings,
    )


def evaluate_treasury_risk_limits(db: Session, lar_simulations: int = 1500) -> TreasuryRiskLimitFrameworkOut:
    lar = calculate_liquidity_at_risk(db, simulations=max(500, lar_simulations), seed=42)
    survival = calculate_liquidity_survival_horizon(db)
    market = calculate_historical_market_risk(db)
    funding = calculate_funding_concentration(db)
    cp_rows = calculate_counterparty_exposure(db)
    max_cp = max((Decimal(x.utilization) for x in cp_rows), default=ZERO)
    metrics = {
        "BUFFER_BREACH_PROBABILITY": Decimal(lar.probability_of_buffer_breach),
        "SURVIVAL_HORIZON_DAYS": Decimal(survival.survival_horizon_days),
        "FX_VAR_95_10D": Decimal(market.portfolio_var),
        "TOP_LENDER_SHARE": Decimal(funding.top_lender_share),
        "MAX_COUNTERPARTY_UTILIZATION": max_cp,
    }
    today = date.today()
    limits = db.scalars(select(TreasuryRiskLimit).where(TreasuryRiskLimit.active.is_(True))).all()
    out: list[TreasuryRiskLimitStatus] = []
    breach = warning = 0
    for lim in limits:
        if lim.effective_from > today or (lim.effective_to and lim.effective_to < today):
            continue
        current = metrics.get(lim.metric_name)
        if current is None:
            continue
        threshold = Decimal(lim.threshold_value)
        warn = Decimal(lim.warning_utilization)
        if lim.comparator == "MIN":
            utilization = threshold / current if current > 0 else None
            if current < threshold:
                status = "BREACH"; breach += 1
            elif current < threshold * warn:
                status = "WARNING"; warning += 1
            else:
                status = "WITHIN_LIMIT"
        else:
            utilization = current / threshold if threshold > 0 else None
            if current > threshold:
                status = "BREACH"; breach += 1
            elif current >= threshold * warn:
                status = "WARNING"; warning += 1
            else:
                status = "WITHIN_LIMIT"
        out.append(TreasuryRiskLimitStatus(
            limit_code=lim.limit_code, category=lim.category, metric_name=lim.metric_name, comparator=lim.comparator,
            threshold_value=threshold, current_value=_q(current, "0.000001" if abs(current) < 10 else "0.01"),
            utilization=_q(utilization, "0.000001") if utilization is not None else None, status=status, owner=lim.owner,
        ))
    overall = "BREACH" if breach else "WARNING" if warning else "WITHIN_LIMITS"
    return TreasuryRiskLimitFrameworkOut(
        overall_status=overall, breach_count=breach, warning_count=warning, rows=out,
        warnings=["Treasury limits are deterministic governance thresholds; exceptions require documented human approval and do not alter source risk calculations."],
    )


def optimize_digital_twin_scenarios(db: Session, request: DigitalTwinOptimizationRequest | None = None, fast_mode: bool = False) -> DigitalTwinOptimizationOut:
    req = request or DigitalTwinOptimizationRequest()
    static_limits = evaluate_treasury_risk_limits(db, lar_simulations=500 if fast_mode else 1500)
    scenarios: list[DigitalTwinOptimizedScenario] = []
    combos = 0
    receivables = [Decimal("0.70"), Decimal("0.90")] if fast_mode else [Decimal("0.65"), Decimal("0.80"), Decimal("0.95")]
    payables = [Decimal("1.05"), Decimal("1.20")] if fast_mode else [Decimal("1.00"), Decimal("1.10"), Decimal("1.20")]
    facilities = [Decimal("0.50"), Decimal("0.90")] if fast_mode else [Decimal("0.50"), Decimal("0.75"), Decimal("1.00")]
    collaterals = [Decimal("1.00")] if fast_mode else [Decimal("0.75"), Decimal("1.00")]
    for receivable in receivables:
        for payable in payables:
            for facility in facilities:
                for collateral_mult in collaterals:
                    combos += 1
                    ir = IntegratedScenarioRequest(
                        label="MVP-11 digital twin grid", weeks=req.weeks,
                        receivable_multiplier=receivable, payable_multiplier=payable, facility_availability=facility,
                        fx_shock_pct=Decimal("0.10"), rate_shock_bps=200,
                        collateral_stress_multiplier=collateral_mult, refinancing_spread_shock_bps=150,
                    )
                    scenario = calculate_integrated_scenario(db, ir)
                    forecast = calculate_custom_liquidity_forecast(db, receivable, payable, facility, req.weeks, "MVP-11 optimizer")
                    survival_days = req.weeks * 7 if forecast.first_buffer_breach_week is None else max((forecast.first_buffer_breach_week - 1) * 7, 0)
                    headroom = Decimal(scenario.stressed_liquidity_headroom_after_overlays)
                    breaches = static_limits.breach_count + (1 if headroom < 0 else 0) + (1 if survival_days < 56 else 0)
                    score = Decimal("100")
                    score -= Decimal(breaches) * Decimal("18")
                    score -= max(Decimal("0.80") - receivable, ZERO) * Decimal("30")
                    score -= max(payable - Decimal("1.05"), ZERO) * Decimal("40")
                    score -= max(Decimal("0.75") - facility, ZERO) * Decimal("35")
                    if headroom < 0:
                        score -= min(abs(headroom) / Decimal("5000000"), Decimal("20"))
                    score = max(score, ZERO)
                    scenarios.append(DigitalTwinOptimizedScenario(
                        rank=0, receivable_multiplier=receivable, payable_multiplier=payable, facility_availability=facility,
                        collateral_stress_multiplier=collateral_mult, stressed_headroom=_q(headroom),
                        first_buffer_breach_week=scenario.first_buffer_breach_week, survival_horizon_days=survival_days,
                        resilience_score=_q(score, "0.01"), limit_breach_count=breaches,
                        status="BREACH" if headroom < 0 else "WATCH" if breaches else "FEASIBLE",
                    ))
    scenarios.sort(key=lambda x: (x.limit_breach_count, -float(x.resilience_score), -float(x.stressed_headroom)))
    top = scenarios[:10]
    top = [x.model_copy(update={"rank": i + 1}) for i, x in enumerate(top)]
    return DigitalTwinOptimizationOut(
        reporting_currency=settings.group_reporting_currency, objective=req.objective, combinations_tested=combos,
        selected_scenario_rank=1, scenarios=top, execution_authority="NONE",
        methodology="Transparent finite grid search ranked by limit compliance, survival, stressed headroom and resilience score; no market prediction or autonomous execution.",
        warnings=["The selected scenario is a decision-support configuration within the tested grid, not a claim of global mathematical optimality or an executable treasury instruction."],
    )
