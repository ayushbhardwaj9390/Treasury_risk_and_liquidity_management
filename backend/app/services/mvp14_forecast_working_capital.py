from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import CashFlow, ForecastPerformanceRecord, LegalEntity, WorkingCapitalObservation
from app.schemas.treasury import (
    ForecastAccuracyOut,
    ForecastAccuracyRow,
    ForecastBiasEntityRow,
    ForecastBiasOut,
    ReceivablesAgingBucket,
    ReceivablesAgingOut,
    ReceivablesCounterpartyRisk,
    WorkingCapitalCycleOut,
    WorkingCapitalCycleRow,
    WorkingCapitalLiquidityBridgeOut,
    WorkingCapitalLiquidityBridgeRequest,
)
from app.services.fx import FXConversionError, convert
from app.services.liquidity import calculate_global_liquidity

ZERO = Decimal("0")
ONE = Decimal("1")


def _q(value: Decimal | int | float, places: str = "0.01") -> Decimal:
    return Decimal(str(value)).quantize(Decimal(places))


def _ratio(numerator: Decimal, denominator: Decimal) -> Decimal:
    return numerator / denominator if denominator != 0 else ZERO


def _reporting(db: Session, amount: Decimal, currency: str, warnings: list[str], label: str) -> Decimal:
    try:
        return convert(db, Decimal(amount), currency, settings.group_reporting_currency)
    except FXConversionError as exc:
        warnings.append(f"{label}: {exc}")
        return ZERO


def _accuracy_status(wape: Decimal, cash_bias: Decimal) -> str:
    if wape <= Decimal("0.10") and abs(cash_bias) <= Decimal("0.05"):
        return "PASS"
    if wape <= Decimal("0.20") and abs(cash_bias) <= Decimal("0.10"):
        return "WATCH"
    return "FAIL"


def _horizon_bucket(days: int) -> str:
    if days <= 7:
        return "0-7D"
    if days <= 30:
        return "8-30D"
    if days <= 90:
        return "31-90D"
    return ">90D"


def calculate_forecast_accuracy(db: Session, lookback_days: int = 180) -> ForecastAccuracyOut:
    if not 30 <= lookback_days <= 730:
        raise ValueError("lookback_days must be between 30 and 730")
    cutoff = date.today() - timedelta(days=lookback_days)
    records = db.scalars(
        select(ForecastPerformanceRecord)
        .where(ForecastPerformanceRecord.target_date >= cutoff, ForecastPerformanceRecord.target_date <= date.today())
        .order_by(ForecastPerformanceRecord.target_date)
    ).all()
    warnings: list[str] = []
    if not records:
        return ForecastAccuracyOut(
            reporting_currency=settings.group_reporting_currency,
            lookback_days=lookback_days,
            observation_count=0,
            overall_wape=ZERO,
            cash_bias_pct=ZERO,
            status="INSUFFICIENT_DATA",
            rows=[],
            warnings=["No realized forecast history is available in the selected lookback window."],
        )

    converted: list[dict] = []
    for r in records:
        forecast = _reporting(db, Decimal(r.forecast_amount), r.currency, warnings, f"Forecast history {r.id}")
        actual = _reporting(db, Decimal(r.actual_amount), r.currency, warnings, f"Forecast history {r.id}")
        cash_error = (forecast - actual) if r.flow_type == "RECEIVABLE" else (actual - forecast)
        converted.append({
            "record": r,
            "forecast": forecast,
            "actual": actual,
            "absolute_error": abs(forecast - actual),
            "cash_error": cash_error,
        })

    total_actual = sum((abs(x["actual"]) for x in converted), ZERO)
    total_abs_error = sum((x["absolute_error"] for x in converted), ZERO)
    total_cash_error = sum((x["cash_error"] for x in converted), ZERO)
    overall_wape = _ratio(total_abs_error, total_actual)
    cash_bias = _ratio(total_cash_error, total_actual)

    rows: list[ForecastAccuracyRow] = []
    for segment_type, keys in (
        ("FLOW_TYPE", sorted({x["record"].flow_type for x in converted})),
        ("HORIZON", ["0-7D", "8-30D", "31-90D", ">90D"]),
    ):
        for key in keys:
            subset = [
                x for x in converted
                if (x["record"].flow_type == key if segment_type == "FLOW_TYPE" else _horizon_bucket(x["record"].horizon_days) == key)
            ]
            if not subset:
                continue
            actual = sum((abs(x["actual"]) for x in subset), ZERO)
            forecast = sum((abs(x["forecast"]) for x in subset), ZERO)
            abs_error = sum((x["absolute_error"] for x in subset), ZERO)
            bias = sum((x["cash_error"] for x in subset), ZERO)
            rows.append(ForecastAccuracyRow(
                segment_type=segment_type,
                segment_value=key,
                observation_count=len(subset),
                forecast_reporting=_q(forecast),
                actual_reporting=_q(actual),
                absolute_error_reporting=_q(abs_error),
                wape=_q(_ratio(abs_error, actual), "0.000001"),
                cash_bias_pct=_q(_ratio(bias, actual), "0.000001"),
            ))

    warnings.extend([
        "Positive cash bias means the historical forecast was optimistic for liquidity: inflows were over-forecast and/or outflows were under-forecast.",
        "Monetary aggregation converts historical local-currency records using the governed reporting-currency conversion layer; accuracy ratios remain based on like-for-like forecast and actual amounts.",
        "WAPE is preferred to MAPE because it remains stable when individual realized flows are small.",
    ])
    return ForecastAccuracyOut(
        reporting_currency=settings.group_reporting_currency,
        lookback_days=lookback_days,
        observation_count=len(converted),
        overall_wape=_q(overall_wape, "0.000001"),
        cash_bias_pct=_q(cash_bias, "0.000001"),
        status=_accuracy_status(overall_wape, cash_bias),
        rows=rows,
        warnings=list(dict.fromkeys(warnings)),
    )


def calculate_forecast_bias(db: Session, lookback_days: int = 180) -> ForecastBiasOut:
    cutoff = date.today() - timedelta(days=lookback_days)
    records = db.scalars(
        select(ForecastPerformanceRecord)
        .where(ForecastPerformanceRecord.target_date >= cutoff, ForecastPerformanceRecord.target_date <= date.today())
    ).all()
    entities = {e.id: e for e in db.scalars(select(LegalEntity)).all()}
    warnings: list[str] = []
    grouped: dict[int, list[ForecastPerformanceRecord]] = defaultdict(list)
    for r in records:
        grouped[r.entity_id].append(r)

    rows: list[ForecastBiasEntityRow] = []
    optimistic = conservative = 0
    for entity_id, group in grouped.items():
        inflow_forecast = inflow_actual = outflow_forecast = outflow_actual = ZERO
        for r in group:
            f = _reporting(db, Decimal(r.forecast_amount), r.currency, warnings, f"Forecast bias {r.id}")
            a = _reporting(db, Decimal(r.actual_amount), r.currency, warnings, f"Forecast bias {r.id}")
            if r.flow_type == "RECEIVABLE":
                inflow_forecast += f
                inflow_actual += a
            elif r.flow_type == "PAYABLE":
                outflow_forecast += f
                outflow_actual += a
        inflow_bias = _ratio(inflow_forecast - inflow_actual, inflow_actual)
        outflow_bias = _ratio(outflow_forecast - outflow_actual, outflow_actual)
        actual_base = inflow_actual + outflow_actual
        cash_bias = _ratio((inflow_forecast - inflow_actual) + (outflow_actual - outflow_forecast), actual_base)
        magnitude = abs(cash_bias)
        status = "PASS" if magnitude <= Decimal("0.05") else "WATCH" if magnitude <= Decimal("0.10") else "FAIL"
        if cash_bias > Decimal("0.05"):
            optimistic += 1
        elif cash_bias < Decimal("-0.05"):
            conservative += 1
        rows.append(ForecastBiasEntityRow(
            entity_name=entities.get(entity_id).name if entities.get(entity_id) else f"Entity {entity_id}",
            inflow_bias_pct=_q(inflow_bias, "0.000001"),
            outflow_bias_pct=_q(outflow_bias, "0.000001"),
            cash_bias_pct=_q(cash_bias, "0.000001"),
            observation_count=len(group),
            status=status,
        ))
    rows.sort(key=lambda x: abs(Decimal(x.cash_bias_pct)), reverse=True)
    warnings.extend([
        "Inflow bias is forecast minus actual; positive values indicate over-forecast collections.",
        "Outflow bias is forecast minus actual; negative values indicate under-forecast payments.",
        "Cash bias combines those directions so positive values consistently mean an optimistic liquidity forecast.",
    ])
    return ForecastBiasOut(
        reporting_currency=settings.group_reporting_currency,
        lookback_days=lookback_days,
        optimistic_bias_entities=optimistic,
        conservative_bias_entities=conservative,
        rows=rows,
        warnings=list(dict.fromkeys(warnings)),
    )


def _wc_metrics(revenue: Decimal, cogs: Decimal, ar: Decimal, ap: Decimal, inventory: Decimal) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    dso = _ratio(ar, revenue) * Decimal("30")
    dpo = _ratio(ap, cogs) * Decimal("30")
    dio = _ratio(inventory, cogs) * Decimal("30")
    return dso, dpo, dio, dso + dio - dpo


def calculate_working_capital_cycle(db: Session) -> WorkingCapitalCycleOut:
    observations = db.scalars(select(WorkingCapitalObservation).order_by(WorkingCapitalObservation.period_end)).all()
    if not observations:
        raise ValueError("No working-capital observations available")
    entities = {e.id: e for e in db.scalars(select(LegalEntity)).all()}
    by_entity: dict[int, list[WorkingCapitalObservation]] = defaultdict(list)
    for o in observations:
        by_entity[o.entity_id].append(o)
    warnings: list[str] = []
    rows: list[WorkingCapitalCycleRow] = []

    latest_records: list[WorkingCapitalObservation] = []
    prior_records: list[WorkingCapitalObservation] = []
    for entity_id, history in by_entity.items():
        history.sort(key=lambda x: x.period_end)
        latest = history[-1]
        prior = history[-2] if len(history) >= 2 else None
        latest_records.append(latest)
        if prior:
            prior_records.append(prior)
        dso, dpo, dio, ccc = _wc_metrics(
            Decimal(latest.revenue), Decimal(latest.cogs), Decimal(latest.receivables_balance), Decimal(latest.payables_balance), Decimal(latest.inventory_balance)
        )
        prior_ccc = None
        if prior:
            prior_ccc = _wc_metrics(Decimal(prior.revenue), Decimal(prior.cogs), Decimal(prior.receivables_balance), Decimal(prior.payables_balance), Decimal(prior.inventory_balance))[3]
        revenue_reporting = _reporting(db, Decimal(latest.revenue), latest.currency, warnings, f"Working capital {latest.id}")
        cogs_reporting = _reporting(db, Decimal(latest.cogs), latest.currency, warnings, f"Working capital {latest.id}")
        rows.append(WorkingCapitalCycleRow(
            entity_name=entities.get(entity_id).name if entities.get(entity_id) else f"Entity {entity_id}",
            period_end=latest.period_end,
            revenue_reporting=_q(revenue_reporting),
            cogs_reporting=_q(cogs_reporting),
            dso_days=_q(dso),
            dpo_days=_q(dpo),
            dio_days=_q(dio),
            ccc_days=_q(ccc),
            prior_ccc_days=None if prior_ccc is None else _q(prior_ccc),
            ccc_change_days=None if prior_ccc is None else _q(ccc - prior_ccc),
        ))

    def aggregate(records: list[WorkingCapitalObservation]) -> tuple[Decimal, Decimal, Decimal, Decimal] | None:
        if not records:
            return None
        rev = cogs = ar = ap = inv = ZERO
        for r in records:
            rev += _reporting(db, Decimal(r.revenue), r.currency, warnings, f"WC aggregate {r.id}")
            cogs += _reporting(db, Decimal(r.cogs), r.currency, warnings, f"WC aggregate {r.id}")
            ar += _reporting(db, Decimal(r.receivables_balance), r.currency, warnings, f"WC aggregate {r.id}")
            ap += _reporting(db, Decimal(r.payables_balance), r.currency, warnings, f"WC aggregate {r.id}")
            inv += _reporting(db, Decimal(r.inventory_balance), r.currency, warnings, f"WC aggregate {r.id}")
        return _wc_metrics(rev, cogs, ar, ap, inv)

    current = aggregate(latest_records)
    prior = aggregate(prior_records)
    assert current is not None
    warnings.extend([
        "DSO, DPO and DIO use monthly revenue/COGS observations normalized to a 30-day period.",
        "Working-capital cycle metrics are management liquidity indicators; accounting definitions should be aligned to the company's chart of accounts before production use.",
    ])
    return WorkingCapitalCycleOut(
        reporting_currency=settings.group_reporting_currency,
        latest_period_end=max(r.period_end for r in latest_records),
        group_dso_days=_q(current[0]),
        group_dpo_days=_q(current[1]),
        group_dio_days=_q(current[2]),
        group_ccc_days=_q(current[3]),
        prior_group_ccc_days=None if prior is None else _q(prior[3]),
        group_ccc_change_days=None if prior is None else _q(current[3] - prior[3]),
        rows=sorted(rows, key=lambda x: x.ccc_days, reverse=True),
        warnings=list(dict.fromkeys(warnings)),
    )


def _aging_bucket(days_overdue: int) -> str:
    if days_overdue <= 0:
        return "CURRENT"
    if days_overdue <= 30:
        return "1-30"
    if days_overdue <= 60:
        return "31-60"
    if days_overdue <= 90:
        return "61-90"
    return "90+"


def calculate_receivables_aging(db: Session) -> ReceivablesAgingOut:
    flows = db.scalars(select(CashFlow).where(CashFlow.flow_type == "RECEIVABLE", CashFlow.status == "OPEN")).all()
    warnings: list[str] = []
    buckets: dict[str, dict[str, Decimal | int]] = {
        key: {"amount": ZERO, "weighted": ZERO, "count": 0} for key in ["CURRENT", "1-30", "31-60", "61-90", "90+"]
    }
    overdue_rows: list[ReceivablesCounterpartyRisk] = []
    total = overdue = weighted = ZERO
    for f in flows:
        amount = _reporting(db, Decimal(f.amount), f.currency, warnings, f"Open receivable {f.id}")
        probability = min(max(Decimal(f.probability), ZERO), ONE)
        days_overdue = (date.today() - f.due_date).days
        bucket = _aging_bucket(days_overdue)
        buckets[bucket]["amount"] += amount
        buckets[bucket]["weighted"] += amount * probability
        buckets[bucket]["count"] += 1
        total += amount
        weighted += amount * probability
        if days_overdue > 0:
            overdue += amount
            overdue_rows.append(ReceivablesCounterpartyRisk(
                counterparty=f.counterparty,
                amount_reporting=_q(amount),
                days_overdue=days_overdue,
                collection_probability=_q(probability, "0.000001"),
            ))
    overdue_rows.sort(key=lambda x: Decimal(x.amount_reporting), reverse=True)
    if _ratio(overdue, total) >= Decimal("0.20"):
        warnings.append("At least 20% of open receivables are overdue in the modeled portfolio; collection actions should be reviewed against customer and commercial context.")
    warnings.append("Collection probability is a treasury forecasting input, not a credit-loss accounting estimate.")
    return ReceivablesAgingOut(
        reporting_currency=settings.group_reporting_currency,
        total_open_receivables=_q(total),
        total_overdue_receivables=_q(overdue),
        overdue_share=_q(_ratio(overdue, total), "0.000001"),
        probability_weighted_open_receivables=_q(weighted),
        buckets=[ReceivablesAgingBucket(
            bucket=key,
            amount_reporting=_q(Decimal(values["amount"])),
            probability_weighted_reporting=_q(Decimal(values["weighted"])),
            invoice_count=int(values["count"]),
        ) for key, values in buckets.items()],
        top_overdue_counterparties=overdue_rows[:10],
        warnings=list(dict.fromkeys(warnings)),
    )


def calculate_working_capital_liquidity_bridge(
    db: Session,
    request: WorkingCapitalLiquidityBridgeRequest,
) -> WorkingCapitalLiquidityBridgeOut:
    observations = db.scalars(select(WorkingCapitalObservation).order_by(WorkingCapitalObservation.period_end)).all()
    if not observations:
        raise ValueError("No working-capital observations available")
    latest_by_entity: dict[int, WorkingCapitalObservation] = {}
    for o in observations:
        if o.entity_id not in latest_by_entity or o.period_end > latest_by_entity[o.entity_id].period_end:
            latest_by_entity[o.entity_id] = o
    warnings: list[str] = []
    revenue = cogs = ZERO
    for o in latest_by_entity.values():
        revenue += _reporting(db, Decimal(o.revenue), o.currency, warnings, f"WC bridge {o.id}")
        cogs += _reporting(db, Decimal(o.cogs), o.currency, warnings, f"WC bridge {o.id}")

    dso_days = max(Decimal(request.dso_improvement_days), ZERO)
    dpo_days = max(Decimal(request.dpo_extension_days), ZERO)
    dio_days = max(Decimal(request.dio_improvement_days), ZERO)
    dso_release = revenue / Decimal("30") * dso_days
    dpo_release = cogs / Decimal("30") * dpo_days
    inventory_release = cogs / Decimal("30") * dio_days
    total_release = dso_release + dpo_release + inventory_release
    current_headroom = Decimal(calculate_global_liquidity(db).liquidity_headroom)
    warnings.extend([
        "The bridge is a management scenario, not a guaranteed cash realization. DSO, DPO and inventory changes require operational execution and may have commercial consequences.",
        "Cash-release components are modeled independently and may interact in practice; treasury should validate feasibility with sales, procurement and operations before action.",
        "Execution authority = NONE. This analysis cannot change customer terms, supplier terms or inventory policy.",
    ])
    return WorkingCapitalLiquidityBridgeOut(
        reporting_currency=settings.group_reporting_currency,
        current_liquidity_headroom=_q(current_headroom),
        dso_cash_release=_q(dso_release),
        dpo_cash_release=_q(dpo_release),
        inventory_cash_release=_q(inventory_release),
        total_modeled_cash_release=_q(total_release),
        pro_forma_liquidity_headroom=_q(current_headroom + total_release),
        execution_authority="NONE",
        warnings=list(dict.fromkeys(warnings)),
    )
