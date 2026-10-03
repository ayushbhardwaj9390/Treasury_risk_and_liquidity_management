from __future__ import annotations

import hashlib
import json
import math
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from statistics import median

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import IsolationForest, RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import brier_score_loss, mean_absolute_error, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import (
    CashFlow,
    DerivativePosition,
    IndependentValuation,
    IntradayPayment,
    LegalEntity,
    MarketDataFeed,
    ModelRegistryEntry,
    PaymentHistory,
    PaymentScreeningCase,
)
from app.schemas.treasury import (
    IntradayBucketOut,
    IntradayLiquidityOut,
    IntradayPaymentPriorityOut,
    IPVSummaryOut,
    IPVTradeOut,
    MarketDataFallbackOut,
    MLCashForecastOut,
    MLForecastPoint,
    ModelDriftOut,
    ModelRegistryOut,
    ModelValidationOut,
    PaymentAnomalyOut,
    PaymentPredictionOut,
    PaymentScreeningOut,
)
from app.services.fx import FXConversionError, convert
from app.services.liquidity import calculate_global_liquidity

ZERO = Decimal("0")
MODEL_CODE = "PAYMENT_BEHAVIOUR_RF"
MODEL_VERSION = "1.0.0"
FEATURES = ["amount_reporting", "terms_days", "invoice_month", "counterparty", "country_code", "currency"]


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _history_frame(db: Session) -> pd.DataFrame:
    rows = db.scalars(select(PaymentHistory).order_by(PaymentHistory.invoice_date, PaymentHistory.id)).all()
    data = []
    for r in rows:
        try:
            amount_reporting = float(convert(db, Decimal(r.amount), r.currency, settings.group_reporting_currency))
        except FXConversionError:
            amount_reporting = 0.0
        delay = max(0, (r.paid_date - r.due_date).days)
        data.append({
            "id": r.id,
            "invoice_date": r.invoice_date,
            "amount_reporting": max(amount_reporting, 0.0),
            "terms_days": int(r.terms_days),
            "invoice_month": int(r.invoice_date.month),
            "counterparty": r.counterparty,
            "country_code": r.country_code,
            "currency": r.currency,
            "delay_days": float(delay),
            "late": int(delay > 0),
        })
    return pd.DataFrame(data)


def _fingerprint(df: pd.DataFrame) -> str:
    if df.empty:
        return "EMPTY"
    raw = df[["id", "invoice_date", "amount_reporting", "terms_days", "delay_days", "late"]].to_csv(index=False).encode()
    return hashlib.sha256(raw).hexdigest()[:24]


def _models(train_df: pd.DataFrame):
    cat = ["counterparty", "country_code", "currency"]
    num = ["amount_reporting", "terms_days", "invoice_month"]
    prep = ColumnTransformer([
        ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), cat),
        ("num", "passthrough", num),
    ])
    classifier = Pipeline([
        ("prep", prep),
        ("model", RandomForestClassifier(
            n_estimators=120, max_depth=7, min_samples_leaf=2, random_state=42, class_weight="balanced_subsample"
        )),
    ])
    regressor = Pipeline([
        ("prep", prep),
        ("model", RandomForestRegressor(
            n_estimators=160, max_depth=7, min_samples_leaf=2, random_state=42
        )),
    ])
    classifier.fit(train_df[FEATURES], train_df["late"])
    regressor.fit(train_df[FEATURES], train_df["delay_days"])
    return classifier, regressor


def _upsert_registry(db: Session, validation: ModelValidationOut) -> None:
    row = db.scalar(select(ModelRegistryEntry).where(ModelRegistryEntry.model_code == MODEL_CODE))
    metrics = json.dumps({
        "mae_delay_days": str(validation.mae_delay_days),
        "brier_score": str(validation.brier_score),
        "auc": None if validation.auc is None else str(validation.auc),
        "validation_rows": validation.validation_rows,
    }, sort_keys=True)
    if row is None:
        row = ModelRegistryEntry(model_code=MODEL_CODE, version=MODEL_VERSION, model_type="RandomForestClassifier+Regressor")
        db.add(row)
    row.version = MODEL_VERSION
    row.trained_at = validation.trained_at
    row.training_rows = validation.training_rows
    row.validation_status = validation.validation_status
    row.metrics_json = metrics
    row.feature_schema = json.dumps(FEATURES)
    row.data_fingerprint = validation.data_fingerprint
    db.commit()


def validate_payment_model(db: Session, persist: bool = True) -> ModelValidationOut:
    df = _history_frame(db)
    if len(df) < 20:
        out = ModelValidationOut(
            model_code=MODEL_CODE, version=MODEL_VERSION, training_rows=len(df), validation_rows=0,
            mae_delay_days=Decimal("0"), brier_score=Decimal("1"), auc=None,
            validation_status="INSUFFICIENT_DATA", trained_at=_now(), data_fingerprint=_fingerprint(df),
        )
        if persist:
            _upsert_registry(db, out)
        return out

    split = max(12, int(len(df) * 0.78))
    split = min(split, len(df) - 8)
    train = df.iloc[:split].copy()
    test = df.iloc[split:].copy()
    clf, reg = _models(train)
    late_prob = clf.predict_proba(test[FEATURES])[:, 1]
    delay_pred = reg.predict(test[FEATURES])
    mae = mean_absolute_error(test["delay_days"], delay_pred)
    brier = brier_score_loss(test["late"], late_prob)
    auc = None
    if len(set(test["late"].tolist())) > 1:
        auc = float(roc_auc_score(test["late"], late_prob))

    if mae <= 8 and brier <= 0.25:
        status = "PASS"
    elif mae <= 14 and brier <= 0.35:
        status = "WATCH"
    else:
        status = "FAIL"

    out = ModelValidationOut(
        model_code=MODEL_CODE,
        version=MODEL_VERSION,
        training_rows=len(train),
        validation_rows=len(test),
        mae_delay_days=Decimal(str(round(mae, 4))),
        brier_score=Decimal(str(round(brier, 6))),
        auc=None if auc is None else Decimal(str(round(auc, 6))),
        validation_status=status,
        trained_at=_now(),
        data_fingerprint=_fingerprint(df),
    )
    if persist:
        _upsert_registry(db, out)
    return out


def _fit_full_payment_models(db: Session):
    df = _history_frame(db)
    if len(df) < 20:
        raise ValueError("Insufficient payment history to fit payment behaviour models")
    clf, reg = _models(df)
    return df, clf, reg


def _open_receivable_frame(db: Session) -> tuple[pd.DataFrame, list[CashFlow]]:
    flows = db.scalars(select(CashFlow).where(CashFlow.flow_type == "RECEIVABLE", CashFlow.status == "OPEN").order_by(CashFlow.due_date)).all()
    data = []
    for f in flows:
        entity = db.get(LegalEntity, f.entity_id)
        try:
            amount_reporting = float(convert(db, Decimal(f.amount), f.currency, settings.group_reporting_currency))
        except FXConversionError:
            amount_reporting = 0.0
        days_to_due = max(1, (f.due_date - date.today()).days)
        terms = 30 if days_to_due < 60 else 45
        data.append({
            "amount_reporting": max(amount_reporting, 0.0),
            "terms_days": terms,
            "invoice_month": int((f.due_date - timedelta(days=terms)).month),
            "counterparty": f.counterparty,
            "country_code": entity.country_code if entity else "XX",
            "currency": f.currency,
        })
    return pd.DataFrame(data), flows


def predict_open_receivables(db: Session) -> list[PaymentPredictionOut]:
    _, clf, reg = _fit_full_payment_models(db)
    x, flows = _open_receivable_frame(db)
    if x.empty:
        return []
    late_prob = clf.predict_proba(x[FEATURES])[:, 1]
    expected = reg.predict(x[FEATURES])
    prep = reg.named_steps["prep"]
    model = reg.named_steps["model"]
    transformed = prep.transform(x[FEATURES])
    tree_preds = np.vstack([tree.predict(transformed) for tree in model.estimators_])
    p10 = np.percentile(tree_preds, 10, axis=0)
    p90 = np.percentile(tree_preds, 90, axis=0)

    out: list[PaymentPredictionOut] = []
    for i, flow in enumerate(flows):
        exp_delay = max(0.0, float(expected[i]))
        low = max(0.0, float(p10[i]))
        high = max(low, float(p90[i]))
        width = high - low
        confidence = "HIGH" if width <= 5 else "MEDIUM" if width <= 12 else "LOW"
        lp = min(max(float(late_prob[i]), 0.0), 1.0)
        out.append(PaymentPredictionOut(
            cash_flow_id=flow.id,
            entity_id=flow.entity_id,
            counterparty=flow.counterparty,
            currency=flow.currency,
            amount=Decimal(flow.amount),
            due_date=flow.due_date,
            on_time_probability=Decimal(str(round(1.0 - lp, 6))),
            late_probability=Decimal(str(round(lp, 6))),
            expected_delay_days=Decimal(str(round(exp_delay, 2))),
            p10_delay_days=Decimal(str(round(low, 2))),
            p90_delay_days=Decimal(str(round(high, 2))),
            expected_receipt_date=flow.due_date + timedelta(days=int(round(exp_delay))),
            confidence=confidence,
        ))
    return out


def _psi(baseline: np.ndarray, recent: np.ndarray) -> float:
    bins = np.array([-0.1, 0.1, 3, 7, 15, 30, 999], dtype=float)
    b, _ = np.histogram(baseline, bins=bins)
    r, _ = np.histogram(recent, bins=bins)
    b = (b + 0.5) / (b.sum() + 0.5 * len(b))
    r = (r + 0.5) / (r.sum() + 0.5 * len(r))
    return float(np.sum((r - b) * np.log(r / b)))


def payment_model_drift(db: Session) -> ModelDriftOut:
    df = _history_frame(db)
    if len(df) < 30:
        return ModelDriftOut(
            model_code=MODEL_CODE, delay_psi=ZERO, late_rate_baseline=ZERO, late_rate_recent=ZERO,
            mean_delay_baseline=ZERO, mean_delay_recent=ZERO, status="INSUFFICIENT_DATA", notes=["At least 30 observations are required."],
        )
    split = int(len(df) * 0.70)
    baseline, recent = df.iloc[:split], df.iloc[split:]
    psi = _psi(baseline["delay_days"].to_numpy(), recent["delay_days"].to_numpy())
    late_b, late_r = float(baseline["late"].mean()), float(recent["late"].mean())
    mean_b, mean_r = float(baseline["delay_days"].mean()), float(recent["delay_days"].mean())
    notes = []
    if psi >= 0.25:
        status = "HIGH"
        notes.append("Payment-delay distribution drift exceeds the high-review threshold.")
    elif psi >= 0.10:
        status = "WATCH"
        notes.append("Payment-delay distribution has shifted and should be monitored.")
    else:
        status = "STABLE"
    if late_r - late_b >= 0.15:
        notes.append("Recent late-payment rate has materially deteriorated versus baseline.")
        if status == "STABLE":
            status = "WATCH"
    return ModelDriftOut(
        model_code=MODEL_CODE,
        delay_psi=Decimal(str(round(psi, 6))),
        late_rate_baseline=Decimal(str(round(late_b, 6))),
        late_rate_recent=Decimal(str(round(late_r, 6))),
        mean_delay_baseline=Decimal(str(round(mean_b, 4))),
        mean_delay_recent=Decimal(str(round(mean_r, 4))),
        status=status,
        notes=notes,
    )


def model_registry(db: Session) -> list[ModelRegistryOut]:
    validate_payment_model(db, persist=True)
    rows = db.scalars(select(ModelRegistryEntry).order_by(ModelRegistryEntry.model_code)).all()
    return [ModelRegistryOut(
        model_code=x.model_code, version=x.version, model_type=x.model_type, trained_at=x.trained_at,
        training_rows=x.training_rows, validation_status=x.validation_status, metrics_json=x.metrics_json,
        feature_schema=x.feature_schema, data_fingerprint=x.data_fingerprint, owner=x.owner,
    ) for x in rows]


def calculate_ml_cash_forecast(db: Session, weeks: int = 13) -> MLCashForecastOut:
    if weeks < 1 or weeks > 52:
        raise ValueError("weeks must be between 1 and 52")
    validation = validate_payment_model(db, persist=True)
    predictions = predict_open_receivables(db)
    pred_by_id = {p.cash_flow_id: p for p in predictions}
    current = calculate_global_liquidity(db)
    start = date.today()
    horizon = start + timedelta(days=weeks * 7 - 1)
    flows = db.scalars(select(CashFlow).where(CashFlow.status == "OPEN", CashFlow.due_date <= horizon + timedelta(days=45))).all()
    cash_e = Decimal(current.deployable_cash)
    cash_c = Decimal(current.deployable_cash)
    cash_o = Decimal(current.deployable_cash)
    facility = Decimal(current.undrawn_credit)
    minimum = Decimal(current.minimum_cash)
    points = []
    warnings: list[str] = []
    first_breach = None

    for w in range(1, weeks + 1):
        ws = start + timedelta(days=(w - 1) * 7)
        we = ws + timedelta(days=6)
        inflow_e = inflow_c = inflow_o = outflows = ZERO
        for f in flows:
            try:
                amt = convert(db, Decimal(f.amount), f.currency, settings.group_reporting_currency)
            except FXConversionError as exc:
                warnings.append(str(exc))
                continue
            if f.flow_type == "PAYABLE" and ws <= f.due_date <= we:
                outflows += amt
            elif f.flow_type == "RECEIVABLE":
                pred = pred_by_id.get(f.id)
                if pred is None:
                    d_e = d_c = d_o = f.due_date
                else:
                    d_e = pred.expected_receipt_date
                    d_c = f.due_date + timedelta(days=int(round(float(pred.p90_delay_days))))
                    d_o = f.due_date + timedelta(days=int(round(float(pred.p10_delay_days))))
                if ws <= d_e <= we:
                    inflow_e += amt
                if ws <= d_c <= we:
                    inflow_c += amt
                if ws <= d_o <= we:
                    inflow_o += amt
        cash_e += inflow_e - outflows
        cash_c += inflow_c - outflows
        cash_o += inflow_o - outflows
        head_e = cash_e + facility - minimum
        head_c = cash_c + facility - minimum
        head_o = cash_o + facility - minimum
        if head_c < 0 and first_breach is None:
            first_breach = w
        points.append(MLForecastPoint(
            week=w, week_start=ws, week_end=we, expected_inflows=inflow_e,
            conservative_inflows=inflow_c, optimistic_inflows=inflow_o, expected_outflows=outflows,
            expected_closing_cash=cash_e, conservative_closing_cash=cash_c, optimistic_closing_cash=cash_o,
            expected_headroom=head_e, conservative_headroom=head_c, optimistic_headroom=head_o,
        ))
    if validation.validation_status in {"WATCH", "FAIL", "INSUFFICIENT_DATA"}:
        warnings.append(f"Payment model validation status is {validation.validation_status}; confidence bands require review.")
    drift = payment_model_drift(db)
    if drift.status in {"WATCH", "HIGH"}:
        warnings.append(f"Payment behaviour drift status is {drift.status}.")
    return MLCashForecastOut(
        reporting_currency=settings.group_reporting_currency,
        model_code=MODEL_CODE,
        version=MODEL_VERSION,
        validation_status=validation.validation_status,
        first_conservative_breach_week=first_breach,
        expected_ending_headroom=points[-1].expected_headroom if points else ZERO,
        conservative_ending_headroom=points[-1].conservative_headroom if points else ZERO,
        optimistic_ending_headroom=points[-1].optimistic_headroom if points else ZERO,
        points=points,
        payment_predictions=predictions,
        warnings=sorted(set(warnings)),
    )


def _entity_liquidity_component(db: Session, entity_id: int):
    liq = calculate_global_liquidity(db)
    for row in liq.entities:
        if row.entity_id == entity_id:
            return row
    raise ValueError(f"Unknown entity {entity_id}")


def _priority_score(payment_type: str, scheduled_at: datetime) -> int:
    base = {
        "TAX": 100, "PAYROLL": 96, "DEBT_SERVICE": 94, "COLLATERAL": 92,
        "CRITICAL_SUPPLIER": 86, "SUPPLIER": 66, "INTERCOMPANY": 55, "DISCRETIONARY": 25,
        "CUSTOMER_RECEIPT": 100,
    }.get(payment_type, 50)
    if scheduled_at.hour <= 11:
        base += 3
    return min(base, 100)


def detect_payment_anomalies(db: Session, entity_id: int | None = None) -> list[PaymentAnomalyOut]:
    stmt = select(IntradayPayment).order_by(IntradayPayment.scheduled_at)
    if entity_id is not None:
        stmt = stmt.where(IntradayPayment.entity_id == entity_id)
    rows = db.scalars(stmt).all()
    if len(rows) < 20:
        return []
    features = []
    valid_rows = []
    type_map: dict[str, int] = {}
    cp_counts: dict[str, int] = {}
    for r in rows:
        cp_counts[r.counterparty] = cp_counts.get(r.counterparty, 0) + 1
        type_map.setdefault(r.payment_type, len(type_map) + 1)
        try:
            amt = float(abs(convert(db, Decimal(r.amount), r.currency, settings.group_reporting_currency)))
        except FXConversionError:
            continue
        features.append([math.log1p(amt), r.scheduled_at.hour + r.scheduled_at.minute / 60, 1 if r.direction == "OUTFLOW" else 0, type_map[r.payment_type]])
        valid_rows.append(r)
    x = np.asarray(features, dtype=float)
    if len(x) < 20:
        return []
    model = IsolationForest(n_estimators=160, contamination=min(0.08, max(0.02, 2 / len(x))), random_state=42)
    labels = model.fit_predict(x)
    scores = -model.decision_function(x)
    today = date.today()
    out = []
    amounts = np.exp(x[:, 0]) - 1
    med = float(np.median(amounts))
    for r, label, score, amt in zip(valid_rows, labels, scores, amounts):
        if r.scheduled_at.date() != today or label != -1:
            continue
        reasons = []
        if med > 0 and amt > med * 4:
            reasons.append("Amount is materially above the intraday payment population median.")
        if r.scheduled_at.hour < 7 or r.scheduled_at.hour > 19:
            reasons.append("Scheduled time is outside the normal operating window.")
        if cp_counts.get(r.counterparty, 0) <= 1:
            reasons.append("Counterparty is new or rare in the available payment history.")
        if not reasons:
            reasons.append("Multivariate payment pattern is unusual versus historical observations.")
        severity = "HIGH" if float(score) > 0.10 else "MEDIUM"
        out.append(PaymentAnomalyOut(
            payment_reference=r.payment_reference, counterparty=r.counterparty, payment_type=r.payment_type,
            amount_reporting=Decimal(str(round(float(amt), 2))), scheduled_at=r.scheduled_at,
            anomaly_score=Decimal(str(round(float(score), 6))), severity=severity, reasons=reasons,
        ))
    return sorted(out, key=lambda x: x.anomaly_score, reverse=True)


def calculate_intraday_liquidity(db: Session, entity_id: int | None = None) -> IntradayLiquidityOut:
    if entity_id is None:
        entity = db.scalar(select(LegalEntity).where(LegalEntity.is_treasury_centre.is_(True)).order_by(LegalEntity.id))
        if entity is None:
            entity = db.scalar(select(LegalEntity).order_by(LegalEntity.id))
    else:
        entity = db.get(LegalEntity, entity_id)
    if entity is None:
        raise ValueError("No legal entity available")
    comp = _entity_liquidity_component(db, entity.id)
    opening = Decimal(comp.deployable_cash_reporting)
    buffer = Decimal(comp.minimum_cash_reporting)
    facility = Decimal(comp.undrawn_credit_reporting)
    rows = db.scalars(select(IntradayPayment).where(
        IntradayPayment.entity_id == entity.id,
        IntradayPayment.scheduled_at >= datetime.combine(date.today(), time.min),
        IntradayPayment.scheduled_at <= datetime.combine(date.today(), time.max),
        IntradayPayment.status.in_(["SCHEDULED", "QUEUED", "HELD"]),
    ).order_by(IntradayPayment.scheduled_at)).all()
    anomalies = {a.payment_reference for a in detect_payment_anomalies(db, entity.id)}
    buckets = [(6, 9), (9, 12), (12, 15), (15, 18), (18, 22)]
    balance = opening
    bucket_out = []
    first_breach = None
    lowest = opening
    priorities = []
    warnings = []
    for start_h, end_h in buckets:
        inflows = outflows = ZERO
        for r in rows:
            if not (start_h <= r.scheduled_at.hour < end_h):
                continue
            try:
                amt = convert(db, Decimal(r.amount), r.currency, settings.group_reporting_currency)
            except FXConversionError as exc:
                warnings.append(str(exc)); continue
            if r.direction == "INFLOW":
                inflows += amt
            else:
                outflows += amt
        balance += inflows - outflows
        lowest = min(lowest, balance)
        head = balance + facility - buffer
        label = f"{start_h:02d}:00-{end_h:02d}:00"
        if head < 0 and first_breach is None:
            first_breach = label
        bucket_out.append(IntradayBucketOut(
            label=label, start_hour=start_h, end_hour=end_h, inflows=inflows, outflows=outflows,
            net_flow=inflows-outflows, projected_balance=balance, minimum_buffer=buffer, headroom=head,
        ))
    for r in rows:
        try:
            amt = convert(db, Decimal(r.amount), r.currency, settings.group_reporting_currency)
        except FXConversionError:
            amt = ZERO
        score = _priority_score(r.payment_type, r.scheduled_at)
        action = "RELEASE_BY_APPROVED_WORKFLOW"
        if r.payment_reference in anomalies:
            action = "MANUAL_REVIEW_ANOMALY"
        elif r.direction == "OUTFLOW" and score < 50 and first_breach:
            action = "HOLD_FOR_LIQUIDITY_REVIEW"
        priorities.append(IntradayPaymentPriorityOut(
            payment_reference=r.payment_reference, counterparty=r.counterparty, direction=r.direction,
            payment_type=r.payment_type, amount_reporting=amt, scheduled_at=r.scheduled_at,
            priority_score=score, recommended_action=action, anomaly_flag=r.payment_reference in anomalies,
        ))
    peak_need = max(buffer - (lowest + facility), ZERO)
    if first_breach:
        warnings.append(f"Intraday liquidity buffer breach projected in {first_breach}.")
    if anomalies:
        warnings.append(f"{len(anomalies)} intraday payment anomaly/anomalies require review before release.")
    priorities.sort(key=lambda x: (-x.priority_score, x.scheduled_at))
    return IntradayLiquidityOut(
        reporting_currency=settings.group_reporting_currency, entity_id=entity.id, entity_name=entity.name,
        opening_deployable_cash=opening, minimum_buffer=buffer, available_committed_facility=facility,
        lowest_projected_balance=lowest, peak_intraday_funding_need=peak_need,
        first_buffer_breach_bucket=first_breach, buckets=bucket_out, payment_priorities=priorities, warnings=sorted(set(warnings)),
    )


def independent_price_verification(db: Session) -> IPVSummaryOut:
    trades = db.scalars(select(DerivativePosition).where(DerivativePosition.status == "OPEN").order_by(DerivativePosition.id)).all()
    rows = []
    warnings = []
    pass_count = warning_count = fail_count = missing_count = 0
    stale_cutoff = _now() - timedelta(hours=24)
    for t in trades:
        vals = db.scalars(select(IndependentValuation).where(
            IndependentValuation.derivative_position_id == t.id,
            IndependentValuation.observed_at >= stale_cutoff,
        ).order_by(IndependentValuation.observed_at.desc())).all()
        book = Decimal(t.market_value_reporting_ccy)
        if not vals:
            status = "MISSING"
            independent = deviation = dev_pct = None
            latest = None
            missing_count += 1
        else:
            independent = Decimal(str(median([float(v.independent_value_reporting_ccy) for v in vals])))
            deviation = abs(book - independent)
            denom = max(abs(independent), Decimal("250000"))
            dev_pct = deviation / denom
            latest = max(v.observed_at for v in vals)
            if deviation > Decimal("250000") and dev_pct > Decimal("0.20"):
                status = "FAIL"; fail_count += 1
            elif deviation > Decimal("100000") or dev_pct > Decimal("0.10"):
                status = "WARN"; warning_count += 1
            else:
                status = "PASS"; pass_count += 1
        rows.append(IPVTradeOut(
            derivative_position_id=t.id, instrument_type=t.instrument_type, counterparty=t.counterparty,
            book_mtm_reporting=book, independent_mid_reporting=independent, absolute_deviation=deviation,
            deviation_pct=dev_pct, independent_source_count=len(vals), latest_observed_at=latest, status=status,
        ))
    if fail_count:
        warnings.append("Independent price verification failures require valuation-control escalation.")
    if missing_count:
        warnings.append("Some open derivatives have no fresh independent valuation source.")
    return IPVSummaryOut(
        reporting_currency=settings.group_reporting_currency, pass_count=pass_count, warning_count=warning_count,
        fail_count=fail_count, missing_count=missing_count, rows=rows, warnings=warnings,
    )


def select_market_data_fallback(db: Session, asset_class: str) -> MarketDataFallbackOut:
    rows = db.scalars(select(MarketDataFeed).where(MarketDataFeed.asset_class == asset_class).order_by(MarketDataFeed.id)).all()
    priority = {"PRIMARY": 0, "SECONDARY": 1, "TERTIARY": 2}
    ranked = sorted(rows, key=lambda x: (priority.get(x.source_type, 9), x.id))
    now = _now()
    for row in ranked:
        age = int(max(0, (now - row.last_received_at).total_seconds() // 60))
        usable = row.status == "ACTIVE" and age <= row.stale_after_minutes
        if usable:
            return MarketDataFallbackOut(
                asset_class=asset_class, selected_feed=row.feed_name, source_type=row.source_type, age_minutes=age,
                fallback_used=row.source_type != "PRIMARY", execution_usable=True,
                reason="Primary source selected." if row.source_type == "PRIMARY" else "Primary source unavailable or stale; approved fallback selected.",
            )
    return MarketDataFallbackOut(
        asset_class=asset_class, selected_feed=None, source_type=None, age_minutes=None,
        fallback_used=False, execution_usable=False, reason="No fresh approved market-data source is available.",
    )


def payment_screening_status(db: Session) -> list[PaymentScreeningOut]:
    rows = db.scalars(select(PaymentScreeningCase).order_by(PaymentScreeningCase.screened_at.desc())).all()
    return [PaymentScreeningOut(
        payment_reference=x.payment_reference, counterparty=x.counterparty, provider=x.provider,
        status=x.status, screened_at=x.screened_at, list_version=x.list_version, reason=x.reason,
        execution_blocked=x.status in {"POTENTIAL_MATCH", "BLOCKED", "PENDING"},
    ) for x in rows]
