from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import BankAccount, CashFlow
from app.schemas.treasury import (
    ForecastDriverOut,
    ForecastDriverRow,
    IntegratedScenarioRequest,
    LiquidityActionPlaybookOut,
    LiquidityAttributionOut,
    LiquidityAttributionRequest,
    LiquidityAttributionRow,
    LiquidityConcentrationOut,
    LiquidityConcentrationRow,
    LiquidityPlaybookAction,
    ProbabilisticLiquidityOut,
    ProbabilisticLiquidityWeek,
)
from app.services.forecast import calculate_liquidity_forecast
from app.services.fx import FXConversionError, convert
from app.services.global_treasury import calculate_cash_mobility
from app.services.integrated_scenario import calculate_integrated_scenario
from app.services.liquidity import calculate_global_liquidity
from app.services.mvp12_liquidity_command import build_contingency_funding_plan

ZERO = Decimal("0")
ONE = Decimal("1")


def _q(value: Decimal | float | int, places: str = "0.01") -> Decimal:
    return Decimal(str(value)).quantize(Decimal(places))


def _share(value: Decimal, total: Decimal) -> Decimal:
    return (value / total) if total > 0 else ZERO


def _hhi(values: list[Decimal]) -> Decimal:
    total = sum(values, ZERO)
    if total <= 0:
        return ZERO
    return sum(((_share(v, total)) ** 2 for v in values if v > 0), ZERO)


def _convert(db: Session, amount: Decimal, currency: str, warnings: list[str], label: str) -> Decimal:
    try:
        return convert(db, amount, currency, settings.group_reporting_currency)
    except FXConversionError as exc:
        warnings.append(f"{label}: {exc}")
        return ZERO


def calculate_liquidity_concentration(db: Session) -> LiquidityConcentrationOut:
    liquidity = calculate_global_liquidity(db)
    mobility = calculate_cash_mobility(db)
    warnings: list[str] = []

    entity_values = {x.entity_name: max(Decimal(x.deployable_cash_reporting), ZERO) for x in liquidity.entities}
    bank_values: dict[str, Decimal] = defaultdict(lambda: ZERO)
    currency_values: dict[str, Decimal] = defaultdict(lambda: ZERO)

    for account in db.scalars(select(BankAccount)).all():
        local = max(
            Decimal(account.book_balance)
            - Decimal(account.restricted_balance)
            - Decimal(account.committed_outflows),
            ZERO,
        )
        reporting = _convert(db, local, account.currency, warnings, f"Bank account {account.id}")
        bank_values[account.bank_name] += reporting
        currency_values[account.currency] += reporting

    def row(dimension: str, values: dict[str, Decimal]) -> LiquidityConcentrationRow:
        total = sum(values.values(), ZERO)
        top_name = max(values, key=values.get) if values else None
        top_value = values.get(top_name, ZERO) if top_name else ZERO
        return LiquidityConcentrationRow(
            dimension=dimension,
            top_name=top_name,
            top_share=_q(_share(top_value, total), "0.000001"),
            hhi=_q(_hhi(list(values.values())), "0.000001"),
            total_reporting=_q(total),
            component_count=len(values),
        )

    rows = [
        row("LEGAL_ENTITY", entity_values),
        row("BANK", dict(bank_values)),
        row("CURRENCY", dict(currency_values)),
    ]
    deployable = Decimal(liquidity.deployable_cash)
    trapped = Decimal(mobility.total_trapped_cash)
    transferable = Decimal(mobility.total_transferable_surplus)
    trapped_share = _share(trapped, deployable)
    transferability_ratio = _share(transferable, deployable)

    for r in rows:
        if Decimal(r.top_share) >= Decimal("0.40"):
            warnings.append(f"{r.dimension} liquidity concentration exceeds 40% in {r.top_name}.")
    if trapped_share >= Decimal("0.20"):
        warnings.append("At least 20% of deployable group cash is classified as trapped under configured mobility restrictions.")
    warnings.append("Concentration uses modeled deployable balances; legal transferability is assessed separately and must not be inferred from bank or currency concentration alone.")

    return LiquidityConcentrationOut(
        reporting_currency=settings.group_reporting_currency,
        deployable_cash=_q(deployable),
        transferable_surplus=_q(transferable),
        trapped_cash=_q(trapped),
        trapped_cash_share=_q(trapped_share, "0.000001"),
        transferability_ratio=_q(transferability_ratio, "0.000001"),
        rows=rows,
        warnings=list(dict.fromkeys(warnings)),
    )


def calculate_probabilistic_liquidity_path(
    db: Session,
    horizon_weeks: int = 13,
    simulations: int = 3000,
    seed: int = 42,
) -> ProbabilisticLiquidityOut:
    if not 1 <= horizon_weeks <= 52:
        raise ValueError("horizon_weeks must be between 1 and 52")
    if not 500 <= simulations <= 20000:
        raise ValueError("simulations must be between 500 and 20000")

    base = calculate_liquidity_forecast(db, "BASE", horizon_weeks)
    inflows = np.array([float(x.expected_inflows) for x in base.points], dtype=float)
    outflows = np.array([float(x.expected_outflows) for x in base.points], dtype=float)
    opening_cash = float(base.points[0].opening_cash if base.points else 0)
    facility = float(base.points[0].available_facility if base.points else 0)
    minimum_buffer = float(base.points[0].minimum_buffer if base.points else 0)

    rng = np.random.default_rng(seed)
    combined_shock = rng.random(simulations) < 0.12
    collection_factor = np.clip(rng.normal(0.96, 0.08, simulations), 0.55, 1.08)
    payable_factor = np.clip(rng.lognormal(0.0, 0.07, simulations), 0.88, 1.35)
    facility_factor = np.clip(rng.beta(9, 2, simulations), 0.25, 1.0)
    if combined_shock.any():
        count = int(combined_shock.sum())
        collection_factor[combined_shock] *= np.clip(rng.normal(0.72, 0.08, count), 0.45, 0.90)
        payable_factor[combined_shock] *= np.clip(rng.normal(1.15, 0.06, count), 1.02, 1.35)
        facility_factor[combined_shock] *= np.clip(rng.normal(0.58, 0.10, count), 0.20, 0.80)

    weekly_collection_noise = np.clip(rng.normal(1.0, 0.06, (simulations, horizon_weeks)), 0.70, 1.20)
    weekly_payable_noise = np.clip(rng.normal(1.0, 0.04, (simulations, horizon_weeks)), 0.85, 1.20)
    simulated_inflows = inflows[None, :] * collection_factor[:, None] * weekly_collection_noise
    simulated_outflows = outflows[None, :] * payable_factor[:, None] * weekly_payable_noise
    cash_paths = opening_cash + np.cumsum(simulated_inflows - simulated_outflows, axis=1)
    headroom = cash_paths + (facility * facility_factor)[:, None] - minimum_buffer

    minimum_headroom = np.min(headroom, axis=1)
    breached = minimum_headroom < 0
    funding_need = np.maximum(-minimum_headroom, 0.0)
    first_breach_weeks: list[int] = []
    for i in np.where(breached)[0]:
        first_breach_weeks.append(int(np.argmax(headroom[i] < 0)) + 1)

    weekly = []
    for idx in range(horizon_weeks):
        h = headroom[:, idx]
        weekly.append(ProbabilisticLiquidityWeek(
            week=idx + 1,
            p05_headroom=_q(np.quantile(h, 0.05)),
            median_headroom=_q(np.quantile(h, 0.50)),
            p95_headroom=_q(np.quantile(h, 0.95)),
            breach_probability=_q(float(np.mean(h < 0)), "0.000001"),
        ))

    breach_probability = float(np.mean(breached))
    warnings = [
        "Probabilistic liquidity is a decision-support distribution, not a guaranteed maximum funding requirement.",
        "Facility availability is modelled stochastically and is not equivalent to a legally confirmed drawdown at every simulation point.",
    ]
    if breach_probability >= 0.05:
        warnings.append("Modeled probability of at least one minimum-buffer breach is at or above 5%; contingency funding and risk appetite should be reviewed.")

    return ProbabilisticLiquidityOut(
        reporting_currency=settings.group_reporting_currency,
        horizon_weeks=horizon_weeks,
        simulations=simulations,
        seed=seed,
        probability_of_any_buffer_breach=_q(breach_probability, "0.000001"),
        expected_first_breach_week_if_breached=_q(float(np.mean(first_breach_weeks)), "0.01") if first_breach_weeks else None,
        p05_minimum_headroom=_q(np.quantile(minimum_headroom, 0.05)),
        median_minimum_headroom=_q(np.quantile(minimum_headroom, 0.50)),
        p95_minimum_headroom=_q(np.quantile(minimum_headroom, 0.95)),
        tail_funding_need_95=_q(np.quantile(funding_need, 0.95)),
        expected_funding_need=_q(np.mean(funding_need)),
        weekly_distribution=weekly,
        methodology="Weekly Monte Carlo path simulation of probability-weighted collections, contractual outflows and committed-facility availability with a low-frequency combined treasury shock regime.",
        warnings=warnings,
    )


def _scenario_request(
    label: str,
    weeks: int,
    receivable_multiplier: Decimal = ONE,
    payable_multiplier: Decimal = ONE,
    facility_availability: Decimal = ONE,
    fx_shock_pct: Decimal = ZERO,
    rate_shock_bps: int = 0,
    collateral_stress_multiplier: Decimal = ZERO,
    refinancing_spread_shock_bps: int = 0,
) -> IntegratedScenarioRequest:
    return IntegratedScenarioRequest(
        label=label,
        weeks=weeks,
        receivable_multiplier=receivable_multiplier,
        payable_multiplier=payable_multiplier,
        facility_availability=facility_availability,
        fx_shock_pct=fx_shock_pct,
        rate_shock_bps=rate_shock_bps,
        collateral_stress_multiplier=collateral_stress_multiplier,
        refinancing_spread_shock_bps=refinancing_spread_shock_bps,
    )


def calculate_liquidity_stress_attribution(db: Session, request: LiquidityAttributionRequest) -> LiquidityAttributionOut:
    base_req = _scenario_request("Attribution base", request.weeks)
    base = calculate_integrated_scenario(db, base_req)
    stressed = calculate_integrated_scenario(db, IntegratedScenarioRequest(**request.model_dump()))
    base_headroom = Decimal(base.stressed_liquidity_headroom_after_overlays)
    stressed_headroom = Decimal(stressed.stressed_liquidity_headroom_after_overlays)

    cases = [
        ("COLLECTIONS", _scenario_request("Collections only", request.weeks, receivable_multiplier=request.receivable_multiplier), "Operating cash receipts / timing"),
        ("PAYABLES", _scenario_request("Payables only", request.weeks, payable_multiplier=request.payable_multiplier), "Operating cash outflows"),
        ("FACILITY_AVAILABILITY", _scenario_request("Facilities only", request.weeks, facility_availability=request.facility_availability), "Committed liquidity capacity"),
        ("FX", _scenario_request("FX only", request.weeks, fx_shock_pct=request.fx_shock_pct), "Economic value unless realized through settlement, collateral or funding"),
        ("RATES", _scenario_request("Rates only", request.weeks, rate_shock_bps=request.rate_shock_bps), "Floating-rate cash interest over scenario horizon"),
        ("COLLATERAL", _scenario_request("Collateral only", request.weeks, collateral_stress_multiplier=request.collateral_stress_multiplier), "Derivative margin / collateral liquidity"),
        ("REFINANCING", _scenario_request("Refinancing only", request.weeks, refinancing_spread_shock_bps=request.refinancing_spread_shock_bps), "Incremental refinancing interest cost"),
    ]

    rows: list[LiquidityAttributionRow] = []
    explained = ZERO
    for driver, req, transmission in cases:
        result = calculate_integrated_scenario(db, req)
        impact = base_headroom - Decimal(result.stressed_liquidity_headroom_after_overlays)
        explained += impact
        rows.append(LiquidityAttributionRow(
            driver=driver,
            standalone_headroom_impact=_q(impact),
            direction="ADVERSE" if impact > 0 else "BENEFICIAL" if impact < 0 else "NEUTRAL",
            liquidity_transmission=transmission,
        ))

    total_deterioration = base_headroom - stressed_headroom
    residual = total_deterioration - explained
    warnings = [
        "Standalone attribution is a finite-difference decomposition; interaction residual captures non-linear and overlapping effects.",
        "FX economic-value shocks are not forced into liquidity unless a modeled cash transmission mechanism exists.",
    ]
    return LiquidityAttributionOut(
        reporting_currency=settings.group_reporting_currency,
        label=request.label,
        base_headroom=_q(base_headroom),
        stressed_headroom=_q(stressed_headroom),
        total_deterioration=_q(total_deterioration),
        explained_deterioration=_q(explained),
        interaction_residual=_q(residual),
        rows=rows,
        warnings=warnings,
    )


def calculate_forecast_driver_concentration(db: Session, horizon_weeks: int = 13, top_n: int = 10) -> ForecastDriverOut:
    if not 1 <= horizon_weeks <= 52:
        raise ValueError("horizon_weeks must be between 1 and 52")
    if not 1 <= top_n <= 50:
        raise ValueError("top_n must be between 1 and 50")
    today = date.today()
    horizon = today + timedelta(days=horizon_weeks * 7)
    flows = db.scalars(select(CashFlow).where(
        CashFlow.status == "OPEN",
        CashFlow.due_date >= today,
        CashFlow.due_date <= horizon,
    )).all()
    warnings: list[str] = []
    aggregated: dict[tuple[str, str, str], Decimal] = defaultdict(lambda: ZERO)
    inflows = ZERO
    outflows = ZERO
    for f in flows:
        amount = _convert(db, Decimal(f.amount), f.currency, warnings, f"Cash flow {f.id}")
        if f.flow_type == "RECEIVABLE":
            amount *= min(max(Decimal(f.probability), ZERO), ONE)
            inflows += amount
        else:
            outflows += amount
        aggregated[(f.counterparty, f.flow_type, f.currency)] += amount

    absolute_base = inflows + outflows
    ordered = sorted(aggregated.items(), key=lambda x: abs(x[1]), reverse=True)
    rows: list[ForecastDriverRow] = []
    for (counterparty, flow_type, currency), amount in ordered[:top_n]:
        signed = amount if flow_type == "RECEIVABLE" else -amount
        rows.append(ForecastDriverRow(
            counterparty=counterparty,
            flow_type=flow_type,
            currency=currency,
            probability_weighted_reporting=_q(amount),
            signed_liquidity_impact=_q(signed),
            share_of_absolute_projected_flows=_q(_share(amount, absolute_base), "0.000001"),
        ))
    largest = Decimal(rows[0].share_of_absolute_projected_flows) if rows else ZERO
    top5 = sum((Decimal(x.share_of_absolute_projected_flows) for x in rows[:5]), ZERO)
    if top5 >= Decimal("0.50"):
        warnings.append("The five largest projected cash-flow drivers represent at least 50% of modeled absolute flows; forecast concentration should be monitored.")
    warnings.append("Receivables are probability-weighted; payables remain contractual. This is concentration analysis, not a forecast-accuracy score.")
    return ForecastDriverOut(
        reporting_currency=settings.group_reporting_currency,
        horizon_weeks=horizon_weeks,
        total_probability_weighted_inflows=_q(inflows),
        total_contractual_outflows=_q(outflows),
        absolute_projected_flow_base=_q(absolute_base),
        largest_driver_share=_q(largest, "0.000001"),
        top_five_driver_share=_q(top5, "0.000001"),
        rows=rows,
        warnings=list(dict.fromkeys(warnings)),
    )


def build_liquidity_action_playbook(db: Session) -> LiquidityActionPlaybookOut:
    cfp = build_contingency_funding_plan(db)
    actions: list[LiquidityPlaybookAction] = []
    quantified = ZERO
    for source in cfp.actions:
        used = Decimal(source.modeled_use_reporting)
        quantified += used
        actions.append(LiquidityPlaybookAction(
            priority=source.stage,
            action=source.action,
            category="QUANTIFIED_EXISTING_LIQUIDITY",
            quantified_capacity_reporting=_q(used),
            lead_time="IMMEDIATE_TO_SHORT" if source.stage <= 2 else "SUBJECT_TO_EXECUTION",
            prerequisites=source.control_requirements,
            execution_authority="NONE",
        ))

    next_priority = max((x.priority for x in actions), default=0) + 1
    actions.extend([
        LiquidityPlaybookAction(
            priority=next_priority,
            action="Accelerate collections from high-value / high-delay counterparties",
            category="WORKING_CAPITAL",
            quantified_capacity_reporting=None,
            lead_time="SHORT",
            prerequisites="Commercial approval, customer-specific collectability assessment and no double counting with forecast assumptions",
            execution_authority="NONE",
        ),
        LiquidityPlaybookAction(
            priority=next_priority + 1,
            action="Review discretionary supplier and capital-expenditure timing",
            category="CASH_CONSERVATION",
            quantified_capacity_reporting=None,
            lead_time="SHORT_TO_MEDIUM",
            prerequisites="Business-owner approval; protect critical suppliers, payroll, tax and contractual obligations",
            execution_authority="NONE",
        ),
        LiquidityPlaybookAction(
            priority=next_priority + 2,
            action="Evaluate new external funding or refinancing structures",
            category="NEW_FUNDING",
            quantified_capacity_reporting=None,
            lead_time="MEDIUM",
            prerequisites="Executable pricing, lender capacity, covenant, tax, legal and approval review",
            execution_authority="NONE",
        ),
    ])
    warnings = list(cfp.warnings)
    warnings.append("Quantified existing-liquidity actions are inherited from the contingency funding plan and are not independently added again to the modeled tail need.")
    warnings.append("Unquantified working-capital and new-funding actions require transaction-specific capacity, pricing and approval evidence before they can reduce a measured shortfall.")
    return LiquidityActionPlaybookOut(
        reporting_currency=settings.group_reporting_currency,
        trigger_status=cfp.status,
        reference_tail_funding_need=Decimal(cfp.reference_tail_funding_need),
        quantified_capacity_total=_q(quantified),
        residual_uncovered_need=Decimal(cfp.uncovered_contingency_need),
        actions=actions,
        warnings=list(dict.fromkeys(warnings)),
    )
