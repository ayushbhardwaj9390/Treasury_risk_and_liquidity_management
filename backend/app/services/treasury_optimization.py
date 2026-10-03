from __future__ import annotations

from decimal import Decimal
from itertools import product

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import CreditFacility, LegalEntity
from app.schemas.treasury import (
    CashPoolOptimizationOut,
    CashSweepInstruction,
    FundingAllocationRow,
    FundingOptimizationOut,
    HedgeOptimizationOut,
    HedgeOptimizationRequest,
    HedgeOptimizationRow,
    IntegratedScenarioRequest,
    ScenarioSearchOut,
    ScenarioSearchRow,
    TreasuryDecisionPackOut,
    TreasuryStrategyRow,
)
from app.services.derivative_risk import calculate_hedge_coverage
from app.services.fx import FXConversionError, convert
from app.services.global_treasury import calculate_cash_mobility, calculate_cash_pools, calculate_cross_border_funding, calculate_collateral_liquidity, calculate_refinancing_risk
from app.services.institutional_risk import calculate_liquidity_at_risk
from app.services.integrated_scenario import calculate_integrated_scenario
from app.services.forecast import calculate_custom_liquidity_forecast
from app.services.market_stress import calculate_market_stress

ZERO = Decimal("0")
ONE = Decimal("1")


def _q(value: Decimal, places: str = "0.01") -> Decimal:
    return Decimal(value).quantize(Decimal(places))


def _bound(value: Decimal, low: Decimal, high: Decimal) -> Decimal:
    return min(max(value, low), high)


def optimize_fx_hedges(db: Session, request: HedgeOptimizationRequest | None = None) -> HedgeOptimizationOut:
    req = request or HedgeOptimizationRequest()
    target_requested = _bound(Decimal(req.target_hedge_ratio), ZERO, ONE)
    option_share = _bound(Decimal(req.option_share), ZERO, ONE)
    shock = max(Decimal(req.fx_shock_pct), ZERO)
    forward_cost_rate = max(Decimal(req.forward_cost_bps), ZERO) / Decimal("10000")
    option_premium = max(Decimal(req.option_premium_pct), ZERO)

    rows: list[HedgeOptimizationRow] = []
    warnings: list[str] = []
    total_incremental_reporting = ZERO
    total_cost_reporting = ZERO

    for h in calculate_hedge_coverage(db):
        underlying = abs(Decimal(h.underlying_exposure))
        current = abs(Decimal(h.hedge_notional))
        if underlying == ZERO:
            rows.append(HedgeOptimizationRow(
                currency=h.currency,
                underlying_exposure=Decimal(h.underlying_exposure),
                current_hedge_notional=Decimal(h.hedge_notional),
                current_hedge_ratio=h.hedge_ratio,
                policy_min=Decimal(h.policy_min),
                policy_max=Decimal(h.policy_max),
                target_hedge_ratio=ZERO,
                incremental_hedge_notional=-current,
                forward_notional=ZERO,
                option_notional=ZERO,
                residual_exposure_after=Decimal(h.residual_exposure),
                adverse_value_sensitivity_after=abs(Decimal(h.residual_exposure)) * shock,
                estimated_execution_liquidity_cost=ZERO,
                action="UNWIND_REVIEW",
                status="UNMATCHED_UNDERLYING",
            ))
            warnings.append(f"{h.currency}: hedge exists without mapped underlying exposure; optimization will not add risk.")
            continue

        target = _bound(target_requested, Decimal(h.policy_min), Decimal(h.policy_max))
        desired = underlying * target
        incremental = desired - current
        action = "ADD_HEDGE" if incremental > ZERO else "REDUCE_HEDGE" if incremental < ZERO else "HOLD"
        add_notional = max(incremental, ZERO)
        forward = add_notional * (ONE - option_share)
        option = add_notional * option_share
        residual = max(underlying - desired, ZERO)

        # Cost inputs are explicit decision assumptions, never inferred market quotes.
        local_cost = forward * forward_cost_rate + option * option_premium
        try:
            incremental_reporting = convert(db, add_notional, h.currency, settings.group_reporting_currency)
            cost_reporting = convert(db, local_cost, h.currency, settings.group_reporting_currency)
        except FXConversionError:
            incremental_reporting = ZERO
            cost_reporting = ZERO
            warnings.append(f"{h.currency}: missing FX conversion; portfolio totals exclude this currency.")

        total_incremental_reporting += incremental_reporting
        total_cost_reporting += cost_reporting
        rows.append(HedgeOptimizationRow(
            currency=h.currency,
            underlying_exposure=Decimal(h.underlying_exposure),
            current_hedge_notional=Decimal(h.hedge_notional),
            current_hedge_ratio=h.hedge_ratio,
            policy_min=Decimal(h.policy_min),
            policy_max=Decimal(h.policy_max),
            target_hedge_ratio=target,
            incremental_hedge_notional=incremental,
            forward_notional=forward,
            option_notional=option,
            residual_exposure_after=residual,
            adverse_value_sensitivity_after=residual * shock,
            estimated_execution_liquidity_cost=local_cost,
            action=action,
            status="POLICY_CONSTRAINED" if target != target_requested else "FEASIBLE",
        ))

    return HedgeOptimizationOut(
        reporting_currency=settings.group_reporting_currency,
        target_hedge_ratio=target_requested,
        total_incremental_hedge_reporting=_q(total_incremental_reporting),
        estimated_execution_liquidity_cost_reporting=_q(total_cost_reporting),
        rows=rows,
        assumptions=[
            "Optimization targets business-exposure hedge ratios within configured policy bands; it does not forecast market direction.",
            f"Illustrative transaction-cost inputs: forwards {req.forward_cost_bps} bps, option premium {req.option_premium_pct} of option notional.",
            "Actual executable quotes, credit charges, CSA effects and accounting designation must be validated before trade approval.",
        ],
        warnings=warnings,
    )


def optimize_funding(db: Session, funding_need: Decimal | None = None, max_cash_mobilization_pct: Decimal = Decimal("0.50")) -> FundingOptimizationOut:
    lar = calculate_liquidity_at_risk(db, simulations=1500, seed=42)
    requested = Decimal(funding_need) if funding_need is not None else Decimal(lar.tail_funding_need)
    requested = max(requested, ZERO)
    mobility = calculate_cash_mobility(db)
    mobilization_pct = _bound(Decimal(max_cash_mobilization_pct), ZERO, ONE)
    internal_cap = Decimal(mobility.total_transferable_surplus) * mobilization_pct
    remaining = requested
    rows: list[FundingAllocationRow] = []

    internal_alloc = min(remaining, internal_cap)
    if internal_alloc > ZERO:
        rows.append(FundingAllocationRow(
            source_type="TRANSFERABLE_GROUP_CASH",
            source_name="Approved transferable surplus",
            capacity_reporting=_q(internal_cap),
            allocated_reporting=_q(internal_alloc),
            estimated_annual_cost_reporting=ZERO,
            cost_rate=ZERO,
            control_status="MOBILITY_RULES_APPLY",
            notes="Allocation is capped by the configured cash-mobilization percentage and excludes trapped cash.",
        ))
        remaining -= internal_alloc

    entities = {x.id: x for x in db.scalars(select(LegalEntity)).all()}
    facilities: list[tuple[Decimal, CreditFacility, str]] = []
    warnings: list[str] = []
    for f in db.scalars(select(CreditFacility).where(CreditFacility.committed.is_(True))).all():
        available_local = max(Decimal(f.limit_amount) - Decimal(f.drawn_amount), ZERO)
        if available_local <= ZERO:
            continue
        try:
            available_reporting = convert(db, available_local, f.currency, settings.group_reporting_currency)
        except FXConversionError:
            warnings.append(f"{f.lender}: facility excluded from optimization because FX conversion is unavailable.")
            continue
        facilities.append((available_reporting, f, entities[f.entity_id].name))

    # No interest spread exists in the current facility master, so capacity is allocated without pretending a cost ranking.
    for capacity, facility, entity_name in sorted(facilities, key=lambda x: x[0], reverse=True):
        if remaining <= ZERO:
            break
        alloc = min(remaining, capacity)
        rows.append(FundingAllocationRow(
            source_type="COMMITTED_EXTERNAL_FACILITY",
            source_name=f"{facility.lender} / {entity_name}",
            capacity_reporting=_q(capacity),
            allocated_reporting=_q(alloc),
            estimated_annual_cost_reporting=None,
            cost_rate=None,
            control_status="PRICING_INPUT_REQUIRED",
            notes="Committed liquidity capacity recognized; facility pricing/spread must be supplied before economic-cost optimization.",
        ))
        remaining -= alloc

    if remaining > ZERO:
        rows.append(FundingAllocationRow(
            source_type="UNFUNDED_CONTINGENCY",
            source_name="New external liquidity required",
            capacity_reporting=ZERO,
            allocated_reporting=_q(remaining),
            estimated_annual_cost_reporting=None,
            cost_rate=None,
            control_status="ESCALATE",
            notes="Existing modeled liquidity sources do not cover the requested contingency need.",
        ))

    ic = calculate_cross_border_funding(db)
    return FundingOptimizationOut(
        reporting_currency=settings.group_reporting_currency,
        requested_funding_need=_q(requested),
        covered_funding=_q(requested - max(remaining, ZERO)),
        uncovered_funding=_q(max(remaining, ZERO)),
        internal_cash_mobilization_cap=_q(internal_cap),
        rows=rows,
        intercompany_structuring_options=ic,
        warnings=warnings + [
            "Intercompany facilities are shown as structuring mechanisms and are not added to group cash capacity to avoid double counting underlying liquidity.",
            "External committed facilities are capacity-ranked only because the current facility master does not contain executable pricing spreads.",
        ],
    )


def optimize_cash_pool(db: Session) -> CashPoolOptimizationOut:
    pools = calculate_cash_pools(db)
    instructions: list[CashSweepInstruction] = []
    warnings: list[str] = []
    total = ZERO

    for pool in pools:
        contributors = [[m.entity_name, Decimal(m.contribution_capacity)] for m in pool.members if Decimal(m.contribution_capacity) > ZERO]
        receivers = [[m.entity_name, Decimal(m.funding_need)] for m in pool.members if Decimal(m.funding_need) > ZERO]
        for receiver in receivers:
            need = receiver[1]
            for contributor in contributors:
                if need <= ZERO:
                    break
                available = contributor[1]
                if available <= ZERO:
                    continue
                amt = min(need, available)
                instructions.append(CashSweepInstruction(
                    pool_name=pool.pool_name,
                    from_entity=contributor[0],
                    to_entity=receiver[0],
                    currency=pool.currency,
                    amount=_q(amt),
                    status="PROPOSED_NOT_EXECUTABLE",
                ))
                contributor[1] -= amt
                need -= amt
                total += amt
            if need > ZERO:
                warnings.append(f"{pool.pool_name}: {receiver[0]} retains {need} {pool.currency} funding need after internal offsets.")

    return CashPoolOptimizationOut(
        total_internal_offset=_q(total),
        instruction_count=len(instructions),
        instructions=instructions,
        warnings=warnings + ["Sweep instructions are analytical proposals only and require tax, legal, policy and maker-checker approval before execution."],
    )


def search_treasury_scenarios(db: Session, top_n: int = 10, compact: bool = False) -> ScenarioSearchOut:
    if compact:
        grids = ([Decimal("0.75"), Decimal("0.60")], [Decimal("1.15"), Decimal("1.30")], [Decimal("0.50"), Decimal("0.25")], [Decimal("0.10")], [200])
    else:
        grids = ([Decimal("0.90"), Decimal("0.75"), Decimal("0.60")], [Decimal("1.00"), Decimal("1.15"), Decimal("1.30")], [Decimal("1.00"), Decimal("0.75"), Decimal("0.50"), Decimal("0.25")], [Decimal("0.05"), Decimal("0.10"), Decimal("0.15")], [100, 200, 300])

    receivables, payables, facilities, fx_shocks, rate_shocks = grids
    # Cache expensive deterministic components. 324 strategy combinations then become cheap composition,
    # rather than 324 repeated full-stack recalculations.
    forecast_cache = {}
    for rec, pay, fac in product(receivables, payables, facilities):
        forecast_cache[(rec, pay, fac)] = calculate_custom_liquidity_forecast(
            db, receivable_multiplier=rec, payable_multiplier=pay, facility_availability=fac, weeks=13, label="MVP9 search"
        )
    market_cache = {(fx, rbps): calculate_market_stress(db, fx, rbps) for fx, rbps in product(fx_shocks, rate_shocks)}
    collateral = calculate_collateral_liquidity(db)
    refinancing = calculate_refinancing_risk(db)
    horizon_fraction = Decimal("13") / Decimal("52")
    incremental_margin = max(Decimal(collateral.stressed_margin_call) - Decimal(collateral.current_margin_call), ZERO) * Decimal("1.25")
    incremental_refi_cost = Decimal(refinancing.debt_due_180d) * Decimal("250") / Decimal("10000") * horizon_fraction

    evaluated = []
    for rec, pay, fac, fx, rbps in product(receivables, payables, facilities, fx_shocks, rate_shocks):
        forecast = forecast_cache[(rec, pay, fac)]
        market = market_cache[(fx, rbps)]
        rate_cash = Decimal(market.annual_rate_cash_impact) * horizon_fraction
        liquidity_call = max(Decimal(market.near_term_derivative_negative_mtm), incremental_margin)
        stressed_headroom = Decimal(forecast.ending_liquidity_headroom) - rate_cash - liquidity_call - incremental_refi_cost
        status = "BREACH" if stressed_headroom < ZERO else "WATCH" if stressed_headroom < Decimal(forecast.maximum_shortfall) + Decimal("10000000") else "RESILIENT"
        evaluated.append((stressed_headroom, forecast, rec, pay, fac, fx, rbps, status))

    evaluated.sort(key=lambda x: x[0])
    rows = []
    for rank, (headroom, forecast, rec, pay, fac, fx, rbps, status) in enumerate(evaluated[:max(1, top_n)], start=1):
        rows.append(ScenarioSearchRow(
            rank=rank, receivable_multiplier=rec, payable_multiplier=pay, facility_availability=fac,
            fx_shock_pct=fx, rate_shock_bps=rbps, stressed_headroom=headroom,
            maximum_shortfall=Decimal(forecast.maximum_shortfall), first_buffer_breach_week=forecast.first_buffer_breach_week, status=status,
        ))
    breach_count = sum(1 for x in evaluated if x[7] == "BREACH")
    return ScenarioSearchOut(
        reporting_currency=settings.group_reporting_currency, combinations_tested=len(evaluated), breach_count=breach_count,
        worst_stressed_headroom=rows[0].stressed_headroom if rows else ZERO, rows=rows,
        methodology="Deterministic grid search across collections, payables, committed-facility availability, FX shock and rate shock with cached integrated collateral/refinancing overlays.",
        warnings=["Scenario search explores configured stress combinations; it is not a probability forecast and does not establish likelihood."],
    )


def build_treasury_decision_pack(db: Session, objective: str = "BALANCED") -> TreasuryDecisionPackOut:
    objective = objective.upper()
    profiles = [
        ("LIQUIDITY_PRESERVATION", "Preserve entity cash buffers and optionality; use lower policy-compliant hedge target.", Decimal("0.60"), Decimal("0.35"), Decimal("0.60")),
        ("BALANCED", "Balance liquidity preservation, hedge coverage and pre-funding of modelled tail need.", Decimal("0.75"), Decimal("0.50"), Decimal("0.80")),
        ("RISK_REDUCTION", "Use the upper hedge-policy band and higher contingency pre-funding while preserving trapped-cash controls.", Decimal("0.90"), Decimal("0.65"), Decimal("1.00")),
    ]
    lar = calculate_liquidity_at_risk(db, simulations=1500, seed=42)
    tail = Decimal(lar.tail_funding_need)
    strategies: list[TreasuryStrategyRow] = []

    for code, description, hedge_target, cash_pct, prefund_pct in profiles:
        hedge = optimize_fx_hedges(db, HedgeOptimizationRequest(target_hedge_ratio=hedge_target))
        target_funding = tail * prefund_pct
        funding = optimize_funding(db, target_funding, cash_pct)
        exceptions = sum(1 for r in hedge.rows if r.status not in {"FEASIBLE", "POLICY_CONSTRAINED"})
        # Transparent internal score: higher funding coverage and lower policy exceptions/cost improve resilience.
        coverage = ZERO if target_funding == ZERO else (Decimal(funding.covered_funding) / target_funding)
        cost_penalty = min(Decimal(hedge.estimated_execution_liquidity_cost_reporting) / Decimal("10000000"), ONE)
        resilience = max(Decimal("0"), min(Decimal("100"), coverage * Decimal("75") + (ONE - cost_penalty) * Decimal("20") - Decimal(exceptions * 5)))
        ext_use = sum(Decimal(x.allocated_reporting) for x in funding.rows if x.source_type == "COMMITTED_EXTERNAL_FACILITY")
        internal_use = sum(Decimal(x.allocated_reporting) for x in funding.rows if x.source_type == "TRANSFERABLE_GROUP_CASH")
        strategies.append(TreasuryStrategyRow(
            strategy_code=code,
            description=description,
            hedge_target_ratio=hedge_target,
            cash_mobilization_pct=cash_pct,
            contingency_prefunding_pct=prefund_pct,
            tail_funding_target=_q(target_funding),
            projected_internal_cash_use=_q(internal_use),
            projected_external_capacity_use=_q(ext_use),
            residual_unfunded_tail=_q(Decimal(funding.uncovered_funding)),
            estimated_hedge_execution_cost=Decimal(hedge.estimated_execution_liquidity_cost_reporting),
            policy_exception_count=exceptions,
            resilience_score=_q(resilience),
            decision_status="FEASIBLE" if Decimal(funding.uncovered_funding) == ZERO and exceptions == 0 else "REVIEW",
        ))

    # Objective selects a policy profile, not a market prediction or autonomous decision.
    valid_codes = {x.strategy_code for x in strategies}
    recommended = objective if objective in valid_codes else "BALANCED"
    search = search_treasury_scenarios(db, top_n=8)
    return TreasuryDecisionPackOut(
        reporting_currency=settings.group_reporting_currency,
        decision_objective=objective,
        recommended_strategy_code=recommended,
        strategies=strategies,
        scenario_search=search,
        human_approval_required=True,
        execution_authority="NONE",
        decision_notes=[
            "The selected strategy reflects the requested treasury objective; it is not an autonomous trade or funding instruction.",
            "All hedge-cost inputs are explicit assumptions and must be replaced with executable market quotes before approval.",
            "Committed facility pricing is incomplete in the current data model, so funding optimization does not claim a cheapest external source.",
            "Astra may compare and explain strategies, but deterministic controls and human approval remain authoritative.",
        ],
    )
