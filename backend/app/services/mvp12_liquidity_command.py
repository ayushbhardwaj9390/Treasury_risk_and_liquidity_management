from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import CashFlow, CreditFacility, DebtPosition, DerivativePosition, LegalEntity
from app.schemas.treasury import (
    BalanceSheetTwinOut,
    BalanceSheetTwinRequest,
    ContingencyFundingAction,
    ContingencyFundingPlanOut,
    CrossCurrencyFundingCandidate,
    CrossCurrencyFundingOut,
    EarlyWarningIndicator,
    EarlyWarningOut,
    FundingTenorBucket,
    FundingTenorOptimizationOut,
    InterestRateGapBucket,
    InterestRateGapDV01Out,
    StructuralLiquidityBucket,
    StructuralLiquidityGapOut,
)
from app.services.advanced_intelligence import calculate_intraday_liquidity, payment_model_drift
from app.services.derivative_risk import calculate_interest_rate_risk
from app.services.digital_twin import run_digital_twin
from app.services.enterprise_controls import latest_reconciliations, market_data_health
from app.services.fx import FXConversionError, convert
from app.services.global_treasury import (
    calculate_cash_mobility,
    calculate_collateral_liquidity,
    calculate_cross_border_funding,
    calculate_refinancing_risk,
)
from app.services.institutional_risk import calculate_liquidity_at_risk
from app.services.integrated_scenario import calculate_integrated_scenario
from app.services.liquidity import calculate_global_liquidity
from app.services.mvp11_risk import (
    calculate_funding_concentration,
    calculate_historical_market_risk,
    calculate_liquidity_survival_horizon,
    evaluate_treasury_risk_limits,
)

ZERO = Decimal("0")
ONE = Decimal("1")
BP = Decimal("0.0001")


def _q(value: Decimal | int | float, places: str = "0.01") -> Decimal:
    return Decimal(str(value)).quantize(Decimal(places))


def _convert(db: Session, amount: Decimal, currency: str, warnings: list[str], label: str) -> Decimal:
    try:
        return convert(db, Decimal(amount), currency, settings.group_reporting_currency)
    except FXConversionError as exc:
        warnings.append(f"{label}: {exc}")
        return ZERO


def _bucket(days: int) -> tuple[str, int, int | None]:
    if days <= 7:
        return ("0-7D", 0, 7)
    if days <= 30:
        return ("8-30D", 8, 30)
    if days <= 90:
        return ("31-90D", 31, 90)
    if days <= 180:
        return ("91-180D", 91, 180)
    if days <= 365:
        return ("181-365D", 181, 365)
    if days <= 730:
        return ("1-2Y", 366, 730)
    return (">2Y", 731, None)


BUCKETS = [
    ("0-7D", 0, 7),
    ("8-30D", 8, 30),
    ("31-90D", 31, 90),
    ("91-180D", 91, 180),
    ("181-365D", 181, 365),
    ("1-2Y", 366, 730),
    (">2Y", 731, None),
]


def calculate_structural_liquidity_gap(db: Session) -> StructuralLiquidityGapOut:
    today = date.today()
    warnings: list[str] = []
    values: dict[str, dict[str, Decimal]] = {
        name: {"inflows": ZERO, "payables": ZERO, "debt": ZERO, "facility_expiry": ZERO}
        for name, _, _ in BUCKETS
    }

    for flow in db.scalars(select(CashFlow).where(CashFlow.status == "OPEN")).all():
        days = max((flow.due_date - today).days, 0)
        name, _, _ = _bucket(days)
        amount = _convert(db, Decimal(flow.amount), flow.currency, warnings, f"Cash flow {flow.id}")
        if flow.flow_type == "RECEIVABLE":
            amount *= max(min(Decimal(flow.probability), ONE), ZERO)
            values[name]["inflows"] += amount
        else:
            values[name]["payables"] += amount

    for debt in db.scalars(select(DebtPosition).where(DebtPosition.status == "OPEN")).all():
        days = max((debt.maturity_date - today).days, 0)
        name, _, _ = _bucket(days)
        values[name]["debt"] += _convert(db, Decimal(debt.principal), debt.currency, warnings, f"Debt {debt.id}")

    for facility in db.scalars(select(CreditFacility).where(CreditFacility.committed.is_(True))).all():
        if facility.maturity_date is None:
            continue
        days = max((facility.maturity_date - today).days, 0)
        name, _, _ = _bucket(days)
        undrawn = max(Decimal(facility.limit_amount) - Decimal(facility.drawn_amount), ZERO)
        values[name]["facility_expiry"] += _convert(db, undrawn, facility.currency, warnings, f"Facility {facility.id}")

    liquidity = calculate_global_liquidity(db)
    cumulative = Decimal(liquidity.deployable_cash)
    rows: list[StructuralLiquidityBucket] = []
    min_cumulative = cumulative
    for name, start, end in BUCKETS:
        v = values[name]
        gap = v["inflows"] - v["payables"] - v["debt"]
        cumulative += gap
        min_cumulative = min(min_cumulative, cumulative)
        rows.append(StructuralLiquidityBucket(
            bucket=name,
            start_day=start,
            end_day=end,
            probability_weighted_inflows=_q(v["inflows"]),
            contractual_payables=_q(v["payables"]),
            debt_maturities=_q(v["debt"]),
            net_contractual_gap=_q(gap),
            cumulative_cash_before_facilities=_q(cumulative),
            committed_facility_capacity_expiring=_q(v["facility_expiry"]),
        ))

    if any(Decimal(r.net_contractual_gap) < 0 for r in rows):
        warnings.append("Negative maturity buckets indicate contractual outflows exceed probability-weighted inflows in those time bands.")
    warnings.append("Committed facilities are shown as contingent liquidity and are not added to contractual cash flows or counted as cash.")
    return StructuralLiquidityGapOut(
        reporting_currency=settings.group_reporting_currency,
        opening_deployable_cash=_q(liquidity.deployable_cash),
        minimum_cash_buffer=_q(liquidity.minimum_cash),
        minimum_cumulative_cash_before_facilities=_q(min_cumulative),
        rows=rows,
        warnings=warnings,
    )


def _debt_duration_years(debt: DebtPosition) -> Decimal:
    days = max((debt.maturity_date - date.today()).days, 1)
    maturity = min(Decimal(days) / Decimal("365"), Decimal("10"))
    if debt.rate_type == "FLOATING":
        # Repricing dates are not yet mastered; use a governed 90-day reset proxy.
        return min(maturity, Decimal("0.25"))
    coupon = max(Decimal(debt.coupon_rate), ZERO)
    return maturity / (ONE + coupon * maturity)


def calculate_interest_rate_gap_dv01(db: Session) -> InterestRateGapDV01Out:
    warnings: list[str] = []
    entities = {e.id: e for e in db.scalars(select(LegalEntity)).all()}
    by_ccy: dict[str, dict[str, Decimal]] = defaultdict(lambda: {
        "fixed": ZERO, "floating": ZERO, "debt_dv01": ZERO, "swap_pay_fixed": ZERO,
        "swap_receive_fixed": ZERO, "swap_dv01": ZERO,
    })

    for debt in db.scalars(select(DebtPosition).where(DebtPosition.status == "OPEN")).all():
        principal = _convert(db, Decimal(debt.principal), debt.currency, warnings, f"Debt {debt.id}")
        ccy = debt.currency
        if debt.rate_type == "FLOATING":
            by_ccy[ccy]["floating"] += principal
        else:
            by_ccy[ccy]["fixed"] += principal
        by_ccy[ccy]["debt_dv01"] += abs(principal * _debt_duration_years(debt) * BP)

    for trade in db.scalars(select(DerivativePosition).where(
        DerivativePosition.status == "OPEN",
        DerivativePosition.instrument_type == "INTEREST_RATE_SWAP",
    )).all():
        notional = abs(_convert(db, Decimal(trade.notional), trade.exposure_currency, warnings, f"IRS {trade.id}"))
        years = min(Decimal(max((trade.maturity_date - date.today()).days, 1)) / Decimal("365"), Decimal("10"))
        pv01 = notional * years * BP
        if trade.hedge_direction == "PAY_FIXED":
            by_ccy[trade.exposure_currency]["swap_pay_fixed"] += notional
            by_ccy[trade.exposure_currency]["swap_dv01"] += pv01
        elif trade.hedge_direction == "RECEIVE_FIXED":
            by_ccy[trade.exposure_currency]["swap_receive_fixed"] += notional
            by_ccy[trade.exposure_currency]["swap_dv01"] -= pv01

    rows: list[InterestRateGapBucket] = []
    total_fixed = total_floating = total_residual = total_debt_dv01 = total_swap_dv01 = ZERO
    for ccy, v in sorted(by_ccy.items()):
        residual_floating = max(v["floating"] - v["swap_pay_fixed"] + v["swap_receive_fixed"], ZERO)
        total_fixed += v["fixed"]
        total_floating += v["floating"]
        total_residual += residual_floating
        total_debt_dv01 += v["debt_dv01"]
        total_swap_dv01 += v["swap_dv01"]
        rows.append(InterestRateGapBucket(
            currency=ccy,
            fixed_debt_reporting=_q(v["fixed"]),
            floating_debt_reporting=_q(v["floating"]),
            pay_fixed_swap_reporting=_q(v["swap_pay_fixed"]),
            receive_fixed_swap_reporting=_q(v["swap_receive_fixed"]),
            residual_floating_reporting=_q(residual_floating),
            debt_dv01_proxy_reporting=_q(v["debt_dv01"]),
            swap_dv01_proxy_reporting=_q(v["swap_dv01"]),
        ))

    rate_risk = calculate_interest_rate_risk(db)
    warnings.extend(rate_risk.warnings)
    warnings.append("DV01 is a transparent parallel-shock proxy. Floating debt assumes a 90-day reset where contractual reset dates are unavailable.")
    warnings.append("Production DV01 should use instrument cash-flow schedules and approved curves rather than this balance-sheet proxy.")
    return InterestRateGapDV01Out(
        reporting_currency=settings.group_reporting_currency,
        fixed_debt_reporting=_q(total_fixed),
        floating_debt_reporting=_q(total_floating),
        residual_floating_reporting=_q(total_residual),
        annual_cash_impact_100bps=_q(total_residual * Decimal("0.01")),
        debt_dv01_proxy_reporting=_q(total_debt_dv01),
        swap_dv01_proxy_reporting=_q(total_swap_dv01),
        combined_dv01_proxy_reporting=_q(total_debt_dv01 + total_swap_dv01),
        rows=rows,
        warnings=warnings,
    )


def optimize_funding_tenor(db: Session, funding_need: Decimal | None = None) -> FundingTenorOptimizationOut:
    lar = calculate_liquidity_at_risk(db, simulations=1500, seed=42)
    concentration = calculate_funding_concentration(db)
    refi = calculate_refinancing_risk(db)
    requested = max(Decimal(funding_need) if funding_need is not None else Decimal(lar.tail_funding_need), ZERO)
    total_funding = max(Decimal(concentration.total_funding_reporting), Decimal("1"))
    near_share = min(Decimal(concentration.funding_due_180d) / total_funding, ONE)

    if near_share >= Decimal("0.30") or Decimal(concentration.top_lender_share) >= Decimal("0.40"):
        weights = [("0-12M", Decimal("0.15")), ("1-3Y", Decimal("0.35")), (">3Y", Decimal("0.50"))]
        rationale = "Current maturity/provider concentration is elevated; the resilience objective shifts incremental funding toward longer tenors."
    else:
        weights = [("0-12M", Decimal("0.25")), ("1-3Y", Decimal("0.40")), (">3Y", Decimal("0.35"))]
        rationale = "Current concentration is moderate; tenor diversification is balanced across short, medium and long maturities."

    rows: list[FundingTenorBucket] = []
    allocated = ZERO
    for idx, (bucket_name, weight) in enumerate(weights):
        amount = _q(requested - allocated) if idx == len(weights) - 1 else _q(requested * weight)
        allocated += amount
        rows.append(FundingTenorBucket(tenor_bucket=bucket_name, target_share=weight, proposed_amount_reporting=amount))
    warnings = [
        "This optimizer targets refinancing resilience, not cheapest funding, because executable all-in pricing is not present in the facility master.",
        "Treasury must validate market capacity, covenants, tax, cross-currency basis, rating impact and documentation before execution.",
    ]
    return FundingTenorOptimizationOut(
        reporting_currency=settings.group_reporting_currency,
        objective="REFINANCING_RESILIENCE",
        requested_new_funding=_q(requested),
        current_funding_due_180d=_q(concentration.funding_due_180d),
        current_top_lender_share=_q(concentration.top_lender_share, "0.0001"),
        current_debt_due_180d=_q(refi.debt_due_180d),
        rows=rows,
        rationale=rationale,
        execution_authority="NONE",
        warnings=warnings,
    )


def analyze_cross_currency_funding(db: Session) -> CrossCurrencyFundingOut:
    mobility = calculate_cash_mobility(db)
    intercompany = calculate_cross_border_funding(db)
    by_borrower: dict[str, list] = defaultdict(list)
    for option in intercompany:
        by_borrower[option.borrower_entity].append(option)

    candidates: list[CrossCurrencyFundingCandidate] = []
    for entity in mobility.entities:
        deficit = Decimal(entity.local_cash_deficit_reporting)
        if deficit <= ZERO:
            continue
        structures: list[str] = ["LOCAL_CURRENCY_EXTERNAL_FUNDING"]
        hedge_required = False
        tax_status = "NOT_APPLICABLE_LOCAL_FUNDING"
        if entity.entity_name in by_borrower:
            structures.append("INTERCOMPANY_FUNDING")
            tax_status = ",".join(sorted({x.tax_review_status for x in by_borrower[entity.entity_name]}))
        structures.append("USD_GROUP_FUNDING_PLUS_FX_HEDGE")
        hedge_required = entity.country_code != "US"
        candidates.append(CrossCurrencyFundingCandidate(
            entity_name=entity.entity_name,
            country_code=entity.country_code,
            local_currency=next((e.functional_currency for e in db.scalars(select(LegalEntity).where(LegalEntity.id == entity.entity_id)).all()), settings.group_reporting_currency),
            funding_need_reporting=_q(deficit),
            candidate_structures=structures,
            hedge_required_for_group_usd_funding=hedge_required,
            pricing_status="LIVE_ALL_IN_PRICING_REQUIRED",
            tax_regulatory_status=tax_status,
        ))

    warnings = [
        "No structure is ranked as cheapest until executable local funding rates, FX forwards/cross-currency basis, fees, tax and regulatory costs are supplied.",
        "Intercompany funding is a structuring option and is not treated as additional group liquidity.",
    ]
    return CrossCurrencyFundingOut(
        reporting_currency=settings.group_reporting_currency,
        candidate_count=len(candidates),
        candidates=candidates,
        decision_status="PRICING_AND_TAX_REVIEW_REQUIRED" if candidates else "NO_LOCAL_DEFICIT",
        execution_authority="NONE",
        warnings=warnings,
    )


def build_contingency_funding_plan(db: Session) -> ContingencyFundingPlanOut:
    liquidity = calculate_global_liquidity(db)
    mobility = calculate_cash_mobility(db)
    lar = calculate_liquidity_at_risk(db, simulations=1500, seed=42)
    survival = calculate_liquidity_survival_horizon(db)
    collateral = calculate_collateral_liquidity(db)
    need = max(Decimal(lar.tail_funding_need), Decimal(collateral.stressed_margin_call), ZERO)

    transferable = max(Decimal(mobility.total_transferable_surplus), ZERO)
    committed = max(Decimal(liquidity.undrawn_credit), ZERO)
    actions: list[ContingencyFundingAction] = []
    remaining = need

    for stage, action, capacity, control in [
        (1, "Mobilize approved transferable group cash", transferable, "CASH_MOBILITY_AND_LOCAL_ENTITY_APPROVALS"),
        (2, "Draw committed external credit facilities", committed, "FACILITY_CONDITIONS_AND_APPROVALS"),
    ]:
        allocated = min(remaining, capacity)
        actions.append(ContingencyFundingAction(stage=stage, action=action, available_capacity_reporting=_q(capacity), modeled_use_reporting=_q(allocated), control_requirements=control))
        remaining -= allocated

    actions.append(ContingencyFundingAction(
        stage=3,
        action="Escalate new external funding / asset-liquidity actions",
        available_capacity_reporting=ZERO,
        modeled_use_reporting=_q(max(remaining, ZERO)),
        control_requirements="CFO_GROUP_TREASURER_BOARD_OR_POLICY_APPROVAL_AS_APPLICABLE",
    ))
    status = "CRISIS" if remaining > ZERO else "ALERT" if survival.survival_horizon_days < 56 else "READY"
    return ContingencyFundingPlanOut(
        reporting_currency=settings.group_reporting_currency,
        status=status,
        reference_tail_funding_need=_q(need),
        survival_horizon_days=survival.survival_horizon_days,
        transferable_cash_capacity=_q(transferable),
        committed_facility_capacity=_q(committed),
        uncovered_contingency_need=_q(max(remaining, ZERO)),
        actions=actions,
        activation_triggers=[
            "Liquidity buffer breach probability exceeds approved threshold",
            "Survival horizon falls below treasury limit",
            "Intraday funding requirement exceeds same-day liquidity capacity",
            "Committed facility availability or key funding provider deteriorates materially",
        ],
        execution_authority="NONE",
        warnings=["Plan capacities are deliberately sequential to reduce double counting of liquidity sources."],
    )


def calculate_early_warning_indicators(db: Session) -> EarlyWarningOut:
    lar = calculate_liquidity_at_risk(db, simulations=1500, seed=42)
    survival = calculate_liquidity_survival_horizon(db)
    intraday = calculate_intraday_liquidity(db)
    funding = calculate_funding_concentration(db)
    market = calculate_historical_market_risk(db)
    limits = evaluate_treasury_risk_limits(db)
    feeds = market_data_health(db)
    recons = latest_reconciliations(db)
    drift = payment_model_drift(db)

    def upper(code: str, value: Decimal, amber: Decimal, red: Decimal, unit: str) -> EarlyWarningIndicator:
        status = "RED" if value >= red else "AMBER" if value >= amber else "GREEN"
        return EarlyWarningIndicator(indicator_code=code, current_value=_q(value, "0.0001"), amber_threshold=_q(amber, "0.0001"), red_threshold=_q(red, "0.0001"), direction="MAX", unit=unit, status=status)

    def lower(code: str, value: Decimal, amber: Decimal, red: Decimal, unit: str) -> EarlyWarningIndicator:
        status = "RED" if value <= red else "AMBER" if value <= amber else "GREEN"
        return EarlyWarningIndicator(indicator_code=code, current_value=_q(value, "0.0001"), amber_threshold=_q(amber, "0.0001"), red_threshold=_q(red, "0.0001"), direction="MIN", unit=unit, status=status)

    stale_feeds = Decimal(sum(1 for f in feeds if not f.execution_usable))
    recon_fail = Decimal(sum(1 for r in recons if r.status == "FAIL"))
    rows = [
        upper("BUFFER_BREACH_PROBABILITY", Decimal(lar.probability_of_buffer_breach), Decimal("0.075"), Decimal("0.10"), "RATIO"),
        lower("SURVIVAL_HORIZON_DAYS", Decimal(survival.survival_horizon_days), Decimal("70"), Decimal("56"), "DAYS"),
        upper("INTRADAY_FUNDING_NEED", Decimal(intraday.peak_intraday_funding_need), Decimal("3000000"), Decimal("7500000"), settings.group_reporting_currency),
        upper("TOP_LENDER_SHARE", Decimal(funding.top_lender_share), Decimal("0.36"), Decimal("0.45"), "RATIO"),
        upper("HISTORICAL_FX_VAR", Decimal(market.portfolio_var), Decimal("1125000"), Decimal("1500000"), settings.group_reporting_currency),
        upper("UNUSABLE_MARKET_FEEDS", stale_feeds, Decimal("1"), Decimal("2"), "COUNT"),
        upper("RECONCILIATION_FAILURES", recon_fail, Decimal("1"), Decimal("2"), "COUNT"),
    ]
    if drift.status not in {"PASS", "NORMAL"}:
        rows.append(EarlyWarningIndicator(indicator_code="PAYMENT_MODEL_DRIFT", current_value=ONE, amber_threshold=ONE, red_threshold=Decimal("2"), direction="MAX", unit="FLAG", status="AMBER"))

    red = sum(1 for x in rows if x.status == "RED")
    amber = sum(1 for x in rows if x.status == "AMBER")
    overall = "RED" if red else "AMBER" if amber else "GREEN"
    return EarlyWarningOut(
        overall_status=overall,
        red_count=red,
        amber_count=amber,
        green_count=sum(1 for x in rows if x.status == "GREEN"),
        indicators=rows,
        governed_limit_status=limits.overall_status,
        warnings=["EWI thresholds are demo governance settings and must be approved against the company's Treasury Risk Appetite Statement before production use."],
    )


def run_balance_sheet_twin(db: Session, request: BalanceSheetTwinRequest | None = None) -> BalanceSheetTwinOut:
    req = request or BalanceSheetTwinRequest()
    integrated = calculate_integrated_scenario(db, req.to_integrated())
    structural = calculate_structural_liquidity_gap(db)
    rate = calculate_interest_rate_gap_dv01(db)
    survival = calculate_liquidity_survival_horizon(
        db,
        weeks=max(req.weeks, 13),
        receivable_multiplier=req.receivable_multiplier,
        payable_multiplier=req.payable_multiplier,
        facility_availability=req.facility_availability,
    )
    twin = run_digital_twin(db)
    incremental_rate_cash = Decimal(rate.residual_floating_reporting) * Decimal(req.rate_shock_bps) / Decimal("10000") * Decimal(req.weeks) / Decimal("52")
    structural_floor = Decimal(structural.minimum_cumulative_cash_before_facilities)
    status = "CRITICAL" if Decimal(integrated.stressed_liquidity_headroom_after_overlays) < ZERO else "WATCH" if survival.survival_horizon_days < 70 else "RESILIENT"
    return BalanceSheetTwinOut(
        version="MVP-12.0",
        reporting_currency=settings.group_reporting_currency,
        scenario_label=req.label,
        status=status,
        stressed_liquidity_headroom=_q(integrated.stressed_liquidity_headroom_after_overlays),
        structural_cash_floor_before_facilities=_q(structural_floor),
        survival_horizon_days=survival.survival_horizon_days,
        first_buffer_breach_week=integrated.first_buffer_breach_week,
        residual_floating_rate_exposure=_q(rate.residual_floating_reporting),
        incremental_rate_cash_impact=_q(incremental_rate_cash),
        fx_economic_value_sensitivity=_q(integrated.fx_economic_value_sensitivity),
        collateral_or_derivative_liquidity_call=_q(integrated.derivative_or_collateral_liquidity_call),
        base_digital_twin_state=twin.state,
        execution_authority="NONE",
        actions=[
            "Review contingency funding actions if survival horizon or buffer thresholds deteriorate.",
            "Rebalance funding tenor where near-term maturities or lender concentration become excessive.",
            "Evaluate hedges only against residual business exposures and approved treasury policy.",
        ],
        warnings=[
            "Balance-sheet twin is a treasury risk simulation, not an accounting balance-sheet forecast.",
            "Rate cash impact uses residual floating exposure; DV01 is reported separately to avoid mixing earnings and valuation sensitivities.",
        ],
    )
