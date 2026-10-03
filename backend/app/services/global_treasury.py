from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import (
    BankAccount,
    CashPool,
    CashPoolMember,
    CashRestriction,
    CollateralAgreement,
    CovenantTest,
    CreditFacility,
    DebtPosition,
    DerivativePosition,
    IntercompanyFacility,
    LegalEntity,
    TaxRule,
)
from app.schemas.treasury import (
    CashMobilityEntity,
    CashMobilityOut,
    CashPoolMemberStatus,
    CashPoolSummary,
    CollateralExposureRow,
    CollateralLiquidityOut,
    CovenantStatusRow,
    CrossBorderFundingOption,
    RefinancingBucket,
    RefinancingRiskOut,
)
from app.services.derivative_risk import PFE_FACTORS
from app.services.fx import FXConversionError, convert
from app.services.liquidity import calculate_global_liquidity

ZERO = Decimal("0")
ONE = Decimal("1")


def _convert_or_zero(db: Session, amount: Decimal, base: str, quote: str, warnings: list[str], label: str) -> Decimal:
    try:
        return convert(db, Decimal(amount), base, quote)
    except FXConversionError as exc:
        warnings.append(f"{label}: {exc}")
        return ZERO


def calculate_cash_mobility(db: Session) -> CashMobilityOut:
    liquidity = calculate_global_liquidity(db)
    entities = {e.id: e for e in db.scalars(select(LegalEntity)).all()}
    today = date.today()
    restrictions = db.scalars(
        select(CashRestriction).where(
            CashRestriction.active.is_(True),
            CashRestriction.effective_from <= today,
        )
    ).all()
    by_entity: dict[int, list[CashRestriction]] = defaultdict(list)
    for row in restrictions:
        if row.effective_to is None or row.effective_to >= today:
            by_entity[row.entity_id].append(row)

    rows: list[CashMobilityEntity] = []
    warnings: list[str] = []
    total_trapped = total_transferable = total_deficit = ZERO

    for component in liquidity.entities:
        entity = entities[component.entity_id]
        extra_restrictions = ZERO
        reasons: list[str] = []
        for restriction in by_entity.get(entity.id, []):
            amount_reporting = _convert_or_zero(
                db,
                Decimal(restriction.restricted_amount),
                restriction.currency,
                settings.group_reporting_currency,
                warnings,
                f"{entity.name}/{restriction.restriction_type}",
            )
            extra_restrictions += max(amount_reporting, ZERO)
            reasons.append(f"{restriction.restriction_type}: {restriction.description}")

        cash_above_minimum = max(component.deployable_cash_reporting - component.minimum_cash_reporting, ZERO)
        trapped = min(extra_restrictions, cash_above_minimum)
        transferable = max(cash_above_minimum - extra_restrictions, ZERO)
        deficit = max(component.minimum_cash_reporting - component.deployable_cash_reporting, ZERO)

        total_trapped += trapped
        total_transferable += transferable
        total_deficit += deficit
        rows.append(CashMobilityEntity(
            entity_id=entity.id,
            entity_name=entity.name,
            country_code=entity.country_code,
            reporting_currency=settings.group_reporting_currency,
            deployable_cash_reporting=component.deployable_cash_reporting,
            minimum_cash_reporting=component.minimum_cash_reporting,
            extra_restrictions_reporting=extra_restrictions,
            transferable_surplus_reporting=transferable,
            local_cash_deficit_reporting=deficit,
            trapped_cash_reporting=trapped,
            restriction_reasons=reasons,
        ))

    if total_trapped > 0:
        warnings.append("Some cash above operating minimums is not immediately transferable because of additional mobility restrictions.")
    if total_deficit > 0 and total_transferable > total_deficit:
        warnings.append("Group surplus cash exists alongside local cash deficits; internal funding or pooling may reduce external borrowing need, subject to tax/regulatory review.")

    return CashMobilityOut(
        reporting_currency=settings.group_reporting_currency,
        total_deployable_cash=liquidity.deployable_cash,
        total_trapped_cash=total_trapped,
        total_transferable_surplus=total_transferable,
        total_local_cash_deficit=total_deficit,
        entities=rows,
        warnings=warnings,
    )


def calculate_cash_pools(db: Session) -> list[CashPoolSummary]:
    entities = {e.id: e for e in db.scalars(select(LegalEntity)).all()}
    mobility = calculate_cash_mobility(db)
    mobility_by_entity = {row.entity_id: row for row in mobility.entities}
    pools = db.scalars(select(CashPool).where(CashPool.active.is_(True)).order_by(CashPool.pool_name)).all()
    out: list[CashPoolSummary] = []

    for pool in pools:
        warnings: list[str] = []
        members = db.scalars(select(CashPoolMember).where(CashPoolMember.cash_pool_id == pool.id)).all()
        rows: list[CashPoolMemberStatus] = []
        total_contrib = total_need = ZERO
        for member in members:
            entity = entities.get(member.entity_id)
            if not entity:
                continue
            accounts = db.scalars(select(BankAccount).where(
                BankAccount.entity_id == member.entity_id,
                BankAccount.currency == pool.currency,
            )).all()
            deployable = sum((Decimal(a.book_balance) - Decimal(a.restricted_balance) - Decimal(a.committed_outflows) for a in accounts), ZERO)
            target = Decimal(member.sweep_target_local)
            raw_contribution = max(deployable - target, ZERO) if member.can_contribute else ZERO
            mobility_row = mobility_by_entity.get(member.entity_id)
            transferable_cap = raw_contribution
            if mobility_row is not None:
                transferable_cap = _convert_or_zero(
                    db,
                    mobility_row.transferable_surplus_reporting,
                    settings.group_reporting_currency,
                    pool.currency,
                    warnings,
                    f"{entity.name}/pool mobility cap",
                )
            contribution = min(raw_contribution, max(transferable_cap, ZERO))
            need = max(target - deployable, ZERO) if member.can_receive else ZERO
            total_contrib += contribution
            total_need += need
            rows.append(CashPoolMemberStatus(
                entity_name=entity.name,
                pool_currency=pool.currency,
                deployable_pool_cash=deployable,
                sweep_target=target,
                contribution_capacity=contribution,
                funding_need=need,
            ))
        internal_offset = min(total_contrib, total_need)
        if total_need > total_contrib:
            warnings.append("Pool funding need exceeds internal contribution capacity; external or intercompany funding outside the pool may be required.")
        out.append(CashPoolSummary(
            pool_name=pool.pool_name,
            pool_type=pool.pool_type,
            currency=pool.currency,
            header_entity=entities.get(pool.header_entity_id).name if entities.get(pool.header_entity_id) else str(pool.header_entity_id),
            total_contribution_capacity=total_contrib,
            total_funding_need=total_need,
            internal_offset_capacity=internal_offset,
            members=rows,
            warnings=warnings,
        ))
    return out


def _tax_rule(db: Session, from_country: str, to_country: str, cash_flow_type: str) -> TaxRule | None:
    today = date.today()
    rows = db.scalars(select(TaxRule).where(
        TaxRule.from_country_code == from_country,
        TaxRule.to_country_code == to_country,
        TaxRule.cash_flow_type == cash_flow_type,
        TaxRule.active.is_(True),
        TaxRule.effective_from <= today,
    ).order_by(TaxRule.effective_from.desc())).all()
    for row in rows:
        if row.effective_to is None or row.effective_to >= today:
            return row
    return None


def calculate_cross_border_funding(db: Session) -> list[CrossBorderFundingOption]:
    entities = {e.id: e for e in db.scalars(select(LegalEntity)).all()}
    facilities = db.scalars(select(IntercompanyFacility).where(IntercompanyFacility.status == "AVAILABLE")).all()
    rows: list[CrossBorderFundingOption] = []
    for facility in facilities:
        lender = entities.get(facility.lender_entity_id)
        borrower = entities.get(facility.borrower_entity_id)
        if not lender or not borrower:
            continue
        available = max(Decimal(facility.limit_amount) - Decimal(facility.drawn_amount), ZERO)
        warnings: list[str] = []
        available_reporting = _convert_or_zero(db, available, facility.currency, settings.group_reporting_currency, warnings, "Intercompany facility")
        annual_interest_reporting = available_reporting * Decimal(facility.interest_rate)

        tp_min = Decimal(facility.transfer_pricing_min_rate) if facility.transfer_pricing_min_rate is not None else None
        tp_max = Decimal(facility.transfer_pricing_max_rate) if facility.transfer_pricing_max_rate is not None else None
        rate = Decimal(facility.interest_rate)
        if tp_min is None or tp_max is None:
            tp_status = "REVIEW_REQUIRED"
        elif tp_min <= rate <= tp_max:
            tp_status = "WITHIN_CONFIGURED_RANGE"
        else:
            tp_status = "OUTSIDE_CONFIGURED_RANGE"

        tax = _tax_rule(db, borrower.country_code, lender.country_code, "INTEREST")
        tax_rate = Decimal(tax.rate) if tax else None
        wht = annual_interest_reporting * tax_rate if tax_rate is not None else None
        tax_status = tax.review_status if tax else "TAX_RULE_MISSING"

        rows.append(CrossBorderFundingOption(
            facility_id=facility.id,
            lender_entity=lender.name,
            borrower_entity=borrower.name,
            lender_country=lender.country_code,
            borrower_country=borrower.country_code,
            currency=facility.currency,
            available_amount=available,
            available_amount_reporting=available_reporting,
            interest_rate=rate,
            transfer_pricing_min_rate=tp_min,
            transfer_pricing_max_rate=tp_max,
            transfer_pricing_status=tp_status,
            withholding_tax_rate=tax_rate,
            estimated_annual_interest_reporting=annual_interest_reporting,
            estimated_annual_withholding_tax_reporting=wht,
            tax_rule_status=tax_status,
            maturity_date=facility.maturity_date,
        ))
    return rows


def _apply_mta(amount: Decimal, mta: Decimal) -> Decimal:
    return ZERO if amount < mta else amount


def calculate_collateral_liquidity(db: Session) -> CollateralLiquidityOut:
    agreements = {x.counterparty: x for x in db.scalars(select(CollateralAgreement).where(CollateralAgreement.active.is_(True))).all()}
    trades = db.scalars(select(DerivativePosition).where(DerivativePosition.status == "OPEN")).all()
    by_counterparty: dict[str, list[DerivativePosition]] = defaultdict(list)
    for trade in trades:
        by_counterparty[trade.counterparty].append(trade)

    rows: list[CollateralExposureRow] = []
    warnings: list[str] = []
    total_current = total_stress = ZERO
    for counterparty, cpty_trades in sorted(by_counterparty.items()):
        agreement = agreements.get(counterparty)
        if agreement is None:
            warnings.append(f"{counterparty}: no active CSA/collateral agreement configured.")
            continue
        net_mtm = sum((Decimal(t.market_value_reporting_ccy) for t in cpty_trades), ZERO)
        stress_addon = ZERO
        for trade in cpty_trades:
            try:
                notional_reporting = abs(convert(db, Decimal(trade.notional), trade.exposure_currency, settings.group_reporting_currency))
            except FXConversionError:
                notional_reporting = ZERO
            stress_addon += notional_reporting * PFE_FACTORS.get(trade.instrument_type, Decimal("0.05"))

        threshold = Decimal(agreement.threshold_reporting_ccy)
        mta = Decimal(agreement.minimum_transfer_amount_reporting_ccy)
        independent = Decimal(agreement.independent_amount_reporting_ccy)
        posted = Decimal(agreement.collateral_posted_reporting_ccy)
        received = Decimal(agreement.collateral_received_reporting_ccy)
        current_adverse = abs(min(net_mtm, ZERO))
        stressed_adverse = current_adverse + stress_addon
        current_call = _apply_mta(max(current_adverse + independent - threshold - posted, ZERO), mta)
        stressed_call = _apply_mta(max(stressed_adverse + independent - threshold - posted, ZERO), mta)
        total_current += current_call
        total_stress += stressed_call
        status = "MARGIN_CALL" if current_call > 0 else "STRESS_WATCH" if stressed_call > 0 else "OK"
        rows.append(CollateralExposureRow(
            counterparty=counterparty,
            net_mtm_reporting=net_mtm,
            threshold_reporting=threshold,
            minimum_transfer_amount_reporting=mta,
            collateral_posted_reporting=posted,
            collateral_received_reporting=received,
            current_margin_call_reporting=current_call,
            stressed_margin_call_reporting=stressed_call,
            status=status,
        ))

    if total_stress > total_current:
        warnings.append("Stressed collateral calls exceed current calls; maintain a separate collateral liquidity buffer to avoid double counting operating cash.")
    return CollateralLiquidityOut(
        reporting_currency=settings.group_reporting_currency,
        current_margin_call=total_current,
        stressed_margin_call=total_stress,
        rows=rows,
        warnings=warnings,
    )


def _covenant_headroom(current: Decimal, threshold: Decimal, direction: str) -> tuple[Decimal, bool]:
    if threshold == 0:
        return ZERO, False
    if direction == "MAX":
        headroom = (threshold - current) / abs(threshold)
        return headroom, current <= threshold
    headroom = (current - threshold) / abs(threshold)
    return headroom, current >= threshold


def calculate_refinancing_risk(db: Session) -> RefinancingRiskOut:
    today = date.today()
    debts = db.scalars(select(DebtPosition).where(DebtPosition.status == "OPEN")).all()
    facilities = db.scalars(select(CreditFacility).where(CreditFacility.committed.is_(True))).all()
    covenants = db.scalars(select(CovenantTest).where(CovenantTest.active.is_(True))).all()
    liquidity = calculate_global_liquidity(db)
    warnings: list[str] = []

    def debt_due(days: int) -> Decimal:
        total = ZERO
        cutoff = today + timedelta(days=days)
        for debt in debts:
            if debt.maturity_date <= cutoff:
                total += _convert_or_zero(db, debt.principal, debt.currency, settings.group_reporting_currency, warnings, f"Debt/{debt.lender}")
        return total

    def facility_due(days: int) -> Decimal:
        total = ZERO
        cutoff = today + timedelta(days=days)
        for facility in facilities:
            if facility.maturity_date and facility.maturity_date <= cutoff:
                undrawn = max(Decimal(facility.limit_amount) - Decimal(facility.drawn_amount), ZERO)
                total += _convert_or_zero(db, undrawn, facility.currency, settings.group_reporting_currency, warnings, f"Facility/{facility.lender}")
        return total

    bucket_specs = [("0-90d", 0, 90), ("91-180d", 90, 180), ("181-365d", 180, 365), (">365d", 365, 36500)]
    maturity_buckets: list[RefinancingBucket] = []
    for label, start, end in bucket_specs:
        debt_total = facility_total = ZERO
        for debt in debts:
            days = (debt.maturity_date - today).days
            if start < days <= end or (start == 0 and 0 <= days <= end):
                debt_total += _convert_or_zero(db, debt.principal, debt.currency, settings.group_reporting_currency, warnings, f"Debt/{debt.lender}")
        for facility in facilities:
            if not facility.maturity_date:
                continue
            days = (facility.maturity_date - today).days
            if start < days <= end or (start == 0 and 0 <= days <= end):
                undrawn = max(Decimal(facility.limit_amount) - Decimal(facility.drawn_amount), ZERO)
                facility_total += _convert_or_zero(db, undrawn, facility.currency, settings.group_reporting_currency, warnings, f"Facility/{facility.lender}")
        maturity_buckets.append(RefinancingBucket(bucket=label, debt_maturing_reporting=debt_total, facility_maturing_reporting=facility_total))

    debt_map = {d.id: d for d in debts}
    covenant_rows: list[CovenantStatusRow] = []
    for covenant in covenants:
        debt = debt_map.get(covenant.debt_position_id)
        if not debt:
            continue
        current = Decimal(covenant.current_value)
        threshold = Decimal(covenant.threshold_value)
        headroom, compliant = _covenant_headroom(current, threshold, covenant.direction)
        warning_buffer = Decimal(covenant.warning_buffer_pct)
        status = "BREACH" if not compliant else "WARNING" if headroom <= warning_buffer else "COMPLIANT"
        covenant_rows.append(CovenantStatusRow(
            debt_position_id=debt.id,
            lender=debt.lender,
            covenant_code=covenant.covenant_code,
            metric_name=covenant.metric_name,
            current_value=current,
            threshold_value=threshold,
            direction=covenant.direction,
            headroom_pct=headroom,
            testing_date=covenant.testing_date,
            status=status,
        ))

    due90 = debt_due(90)
    due180 = debt_due(180)
    due365 = debt_due(365)
    fac90 = facility_due(90)
    ratio = due365 / liquidity.liquidity_headroom if liquidity.liquidity_headroom > 0 else None
    if due180 > 0:
        warnings.append("Debt matures within 180 days; refinancing execution and committed backup capacity should be tracked.")
    if fac90 > 0:
        warnings.append("Committed facilities expire within 90 days; do not count expiring undrawn capacity as durable liquidity without renewal visibility.")
    if any(c.status == "BREACH" for c in covenant_rows):
        warnings.append("At least one configured covenant is in breach; treasury should assess waiver, acceleration, and liquidity consequences.")
    elif any(c.status == "WARNING" for c in covenant_rows):
        warnings.append("Covenant headroom is approaching a configured warning buffer.")

    return RefinancingRiskOut(
        reporting_currency=settings.group_reporting_currency,
        debt_due_90d=due90,
        debt_due_180d=due180,
        debt_due_365d=due365,
        committed_facilities_due_90d=fac90,
        liquidity_headroom=liquidity.liquidity_headroom,
        debt_due_365d_to_headroom=ratio,
        maturity_buckets=maturity_buckets,
        covenants=covenant_rows,
        warnings=warnings,
    )
