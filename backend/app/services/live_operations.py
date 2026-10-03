from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, InvalidOperation

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.observability import observe_execution_message, observe_treasury_event
from app.models import (
    AuditLog,
    BankAccount,
    CashFlow,
    ConnectorCheckpoint,
    ExecutionMessage,
    FXRate,
    IntradayPayment,
    LegalEntity,
    LiveTreasuryAlert,
    SourceConnector,
    TransactionProposal,
    TreasuryEvent,
    UserAccount,
)
from app.schemas.treasury import (
    ConnectorCheckpointOut,
    EventIngestionResult,
    EventReplayResult,
    ExecutionMessageOut,
    LiveMonitorRunOut,
    LiveOperationsStatusOut,
    LiveTreasuryAlertOut,
    TreasuryEventIn,
    TreasuryEventOut,
)
from app.services.advanced_intelligence import calculate_intraday_liquidity
from app.services.enterprise_controls import connector_health
from app.services.institutional_risk import calculate_liquidity_at_risk
from app.services.liquidity import calculate_global_liquidity

ZERO = Decimal("0")
SUPPORTED_SCHEMA_VERSIONS = {"1.0"}
SUPPORTED_EVENT_TYPES = {
    "BANK_BALANCE",
    "MARKET_FX_QUOTE",
    "ERP_CASH_FLOW",
    "PAYMENT_STATUS",
    "CONNECTOR_HEARTBEAT",
    "EXECUTION_ACK",
}


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _canonical_json(payload: dict) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def _hash(payload_json: str) -> str:
    return hashlib.sha256(payload_json.encode("utf-8")).hexdigest()


def _decimal(value, field: str) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"Invalid decimal for {field}") from exc


def _date(value, field: str) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise ValueError(f"Invalid ISO date for {field}") from exc


def _event_out(row: TreasuryEvent) -> TreasuryEventOut:
    return TreasuryEventOut(
        id=row.id,
        source_system=row.source_system,
        connector_name=row.connector_name,
        event_type=row.event_type,
        idempotency_key=row.idempotency_key,
        event_time=row.event_time,
        received_at=row.received_at,
        entity_id=row.entity_id,
        external_reference=row.external_reference,
        sequence_no=row.sequence_no,
        schema_version=row.schema_version,
        payload_hash=row.payload_hash,
        processing_status=row.processing_status,
        processing_error=row.processing_error,
        replay_count=row.replay_count,
    )


def _checkpoint_out(row: ConnectorCheckpoint) -> ConnectorCheckpointOut:
    lag = None
    if row.last_event_time:
        lag = max(0, int((_now() - row.last_event_time).total_seconds()))
    return ConnectorCheckpointOut(
        connector_name=row.connector_name,
        source_system=row.source_system,
        last_sequence_no=row.last_sequence_no,
        last_event_time=row.last_event_time,
        last_received_at=row.last_received_at,
        lag_seconds=lag,
        accepted_count=row.accepted_count,
        duplicate_count=row.duplicate_count,
        quarantined_count=row.quarantined_count,
        failed_count=row.failed_count,
        status=row.status,
    )


def _alert_out(row: LiveTreasuryAlert) -> LiveTreasuryAlertOut:
    return LiveTreasuryAlertOut(
        id=row.id,
        alert_key=row.alert_key,
        category=row.category,
        severity=row.severity,
        title=row.title,
        message=row.message,
        source_event_id=row.source_event_id,
        status=row.status,
        created_at=row.created_at,
        last_seen_at=row.last_seen_at,
        acknowledged_by=row.acknowledged_by,
        acknowledged_at=row.acknowledged_at,
    )


def _execution_out(row: ExecutionMessage) -> ExecutionMessageOut:
    return ExecutionMessageOut(
        id=row.id,
        message_id=row.message_id,
        proposal_id=row.proposal_id,
        connector_name=row.connector_name,
        idempotency_key=row.idempotency_key,
        payload_hash=row.payload_hash,
        signature=row.signature,
        status=row.status,
        created_by=row.created_by,
        created_at=row.created_at,
        sent_at=row.sent_at,
        acknowledged_at=row.acknowledged_at,
        external_reference=row.external_reference,
        acknowledgement_detail=row.acknowledgement_detail,
    )


def _ensure_checkpoint(db: Session, request: TreasuryEventIn) -> ConnectorCheckpoint:
    row = db.scalar(select(ConnectorCheckpoint).where(ConnectorCheckpoint.connector_name == request.connector_name))
    if row is None:
        row = ConnectorCheckpoint(
            connector_name=request.connector_name,
            source_system=request.source_system,
            status="ACTIVE",
        )
        db.add(row)
        db.flush()
    return row


def _refresh_connector(db: Session, connector_name: str, received_at: datetime) -> None:
    connector = db.scalar(select(SourceConnector).where(SourceConnector.connector_name == connector_name))
    if connector:
        connector.last_success_at = received_at
        if connector.status != "ACTIVE":
            connector.status = "ACTIVE"


def _upsert_alert(
    db: Session,
    *,
    alert_key: str,
    category: str,
    severity: str,
    title: str,
    message: str,
    source_event_id: int | None = None,
) -> LiveTreasuryAlert:
    now = _now()
    row = db.scalar(select(LiveTreasuryAlert).where(LiveTreasuryAlert.alert_key == alert_key))
    if row is None:
        row = LiveTreasuryAlert(
            alert_key=alert_key,
            category=category,
            severity=severity,
            title=title,
            message=message,
            source_event_id=source_event_id,
            status="OPEN",
            created_at=now,
            last_seen_at=now,
        )
        db.add(row)
        db.flush()
    else:
        row.category = category
        row.severity = severity
        row.title = title
        row.message = message
        row.source_event_id = source_event_id or row.source_event_id
        row.last_seen_at = now
        if row.status == "RESOLVED":
            row.status = "OPEN"
            row.acknowledged_by = None
            row.acknowledged_at = None
    return row


def _apply_event(db: Session, event: TreasuryEvent, payload: dict) -> tuple[bool, list[int]]:
    """Project an immutable event into current-state tables.

    The ledger remains the evidence source. Projection tables are disposable current-state views.
    """
    alert_ids: list[int] = []
    etype = event.event_type

    if etype == "BANK_BALANCE":
        account_id = int(payload["account_id"])
        account = db.get(BankAccount, account_id)
        if account is None:
            raise ValueError(f"Bank account {account_id} not found")
        if event.event_time < account.last_updated:
            event.processing_status = "QUARANTINED_OUT_OF_ORDER"
            event.processing_error = "Bank balance event predates current account state"
            return False, alert_ids
        account.book_balance = _decimal(payload["book_balance"], "book_balance")
        if "restricted_balance" in payload:
            account.restricted_balance = _decimal(payload["restricted_balance"], "restricted_balance")
        if "committed_outflows" in payload:
            account.committed_outflows = _decimal(payload["committed_outflows"], "committed_outflows")
        account.last_updated = event.event_time
        return True, alert_ids

    if etype == "MARKET_FX_QUOTE":
        base = str(payload["base_currency"]).upper()
        quote = str(payload["quote_currency"]).upper()
        rate = _decimal(payload["rate"], "rate")
        if rate <= ZERO:
            raise ValueError("FX rate must be positive")
        latest = db.scalar(
            select(FXRate)
            .where(FXRate.base_currency == base, FXRate.quote_currency == quote)
            .order_by(FXRate.as_of.desc())
            .limit(1)
        )
        if latest and event.event_time < latest.as_of:
            event.processing_status = "QUARANTINED_OUT_OF_ORDER"
            event.processing_error = "Market quote predates current quote state"
            return False, alert_ids
        prior = Decimal(latest.rate) if latest else None
        db.add(FXRate(
            base_currency=base,
            quote_currency=quote,
            rate=rate,
            as_of=event.event_time,
            source=str(payload.get("source", event.source_system)),
        ))
        if prior and prior > ZERO:
            move = abs(rate / prior - Decimal("1"))
            if move >= Decimal("0.05"):
                alert = _upsert_alert(
                    db,
                    alert_key=f"FX_MOVE:{base}{quote}",
                    category="MARKET_MOVE",
                    severity="HIGH" if move >= Decimal("0.10") else "MEDIUM",
                    title=f"Large {base}/{quote} market move",
                    message=f"Latest event moved {base}/{quote} by {move * 100:.2f}% versus the preceding governed quote.",
                    source_event_id=event.id,
                )
                alert_ids.append(alert.id)
        return True, alert_ids

    if etype == "ERP_CASH_FLOW":
        source_ref = event.external_reference or str(payload["source_reference"])
        row = db.scalar(select(CashFlow).where(CashFlow.source_reference == source_ref))
        entity_id = event.entity_id or int(payload["entity_id"])
        if db.get(LegalEntity, entity_id) is None:
            raise ValueError(f"Legal entity {entity_id} not found")
        values = dict(
            entity_id=entity_id,
            flow_type=str(payload["flow_type"]).upper(),
            counterparty=str(payload["counterparty"]),
            currency=str(payload["currency"]).upper(),
            amount=_decimal(payload["amount"], "amount"),
            due_date=_date(payload["due_date"], "due_date"),
            probability=_decimal(payload.get("probability", "1"), "probability"),
            status=str(payload.get("status", "OPEN")).upper(),
            source_reference=source_ref,
        )
        if values["flow_type"] not in {"RECEIVABLE", "PAYABLE"}:
            raise ValueError("flow_type must be RECEIVABLE or PAYABLE")
        if row is None:
            db.add(CashFlow(**values))
        else:
            for key, value in values.items():
                setattr(row, key, value)
        return True, alert_ids

    if etype == "PAYMENT_STATUS":
        reference = event.external_reference or str(payload["payment_reference"])
        row = db.scalar(select(IntradayPayment).where(IntradayPayment.payment_reference == reference))
        if row is None:
            raise ValueError(f"Intraday payment {reference} not found")
        row.status = str(payload["status"]).upper()
        return True, alert_ids

    if etype == "CONNECTOR_HEARTBEAT":
        _refresh_connector(db, event.connector_name, event.received_at)
        return True, alert_ids

    if etype == "EXECUTION_ACK":
        message_id = str(payload["message_id"])
        row = db.scalar(select(ExecutionMessage).where(ExecutionMessage.message_id == message_id))
        if row is None:
            raise ValueError(f"Execution message {message_id} not found")
        status = str(payload["status"]).upper()
        if status not in {"ACKNOWLEDGED", "REJECTED"}:
            raise ValueError("Execution acknowledgement status must be ACKNOWLEDGED or REJECTED")
        row.status = status
        row.acknowledged_at = event.event_time
        row.external_reference = payload.get("external_reference")
        row.acknowledgement_detail = str(payload.get("detail", ""))
        return True, alert_ids

    raise ValueError(f"Unsupported event_type {etype}")


def ingest_treasury_event(db: Session, request: TreasuryEventIn) -> EventIngestionResult:
    payload_json = _canonical_json(request.payload)
    payload_hash = _hash(payload_json)
    existing = db.scalar(select(TreasuryEvent).where(TreasuryEvent.idempotency_key == request.idempotency_key))
    if existing:
        if existing.payload_hash != payload_hash or existing.connector_name != request.connector_name or existing.event_type != request.event_type.upper():
            raise ValueError("Idempotency key collision: the same key was reused for different event content")
        checkpoint = _ensure_checkpoint(db, request)
        checkpoint.duplicate_count += 1
        checkpoint.last_received_at = _now()
        observe_treasury_event(existing.event_type, "DUPLICATE")
        db.add(AuditLog(
            event_type="TREASURY_EVENT_DUPLICATE",
            actor=request.connector_name,
            details=f"event_id={existing.id}; idempotency_key={request.idempotency_key}",
        ))
        db.commit()
        return EventIngestionResult(event=_event_out(existing), duplicate=True, projected=existing.processing_status == "APPLIED", alert_ids=[])

    now = _now()
    event = TreasuryEvent(
        idempotency_key=request.idempotency_key,
        event_type=request.event_type.upper(),
        source_system=request.source_system,
        connector_name=request.connector_name,
        entity_id=request.entity_id,
        external_reference=request.external_reference,
        sequence_no=request.sequence_no,
        schema_version=request.schema_version,
        event_time=request.event_time.replace(tzinfo=None) if request.event_time.tzinfo else request.event_time,
        received_at=now,
        payload_hash=payload_hash,
        payload_json=payload_json,
        processing_status="RECEIVED",
    )
    db.add(event)
    db.flush()
    checkpoint = _ensure_checkpoint(db, request)

    projected = False
    alert_ids: list[int] = []
    try:
        if request.schema_version not in SUPPORTED_SCHEMA_VERSIONS:
            event.processing_status = "QUARANTINED_SCHEMA"
            event.processing_error = f"Unsupported schema version {request.schema_version}"
            checkpoint.quarantined_count += 1
        elif event.event_type not in SUPPORTED_EVENT_TYPES:
            event.processing_status = "QUARANTINED_EVENT_TYPE"
            event.processing_error = f"Unsupported event type {event.event_type}"
            checkpoint.quarantined_count += 1
        elif request.sequence_no is not None and checkpoint.last_sequence_no is not None and request.sequence_no <= checkpoint.last_sequence_no:
            event.processing_status = "QUARANTINED_SEQUENCE"
            event.processing_error = "Sequence number is not newer than the connector checkpoint"
            checkpoint.quarantined_count += 1
        else:
            projected, alert_ids = _apply_event(db, event, request.payload)
            if event.processing_status.startswith("QUARANTINED"):
                checkpoint.quarantined_count += 1
            else:
                event.processing_status = "APPLIED" if projected else "ACCEPTED"
                checkpoint.accepted_count += 1
                checkpoint.last_event_time = event.event_time
                checkpoint.last_received_at = event.received_at
                if request.sequence_no is not None:
                    checkpoint.last_sequence_no = request.sequence_no
                checkpoint.status = "ACTIVE"
                _refresh_connector(db, request.connector_name, event.received_at)
    except Exception as exc:
        event.processing_status = "FAILED"
        event.processing_error = str(exc)[:500]
        checkpoint.failed_count += 1
        checkpoint.last_received_at = event.received_at

    observe_treasury_event(event.event_type, event.processing_status)
    db.add(AuditLog(
        event_type="TREASURY_EVENT_INGESTED",
        actor=request.connector_name,
        details=(
            f"event_id={event.id}; type={event.event_type}; status={event.processing_status}; "
            f"source={event.source_system}; external_reference={event.external_reference or ''}"
        ),
    ))
    db.commit()
    db.refresh(event)
    return EventIngestionResult(event=_event_out(event), duplicate=False, projected=projected, alert_ids=alert_ids)


def replay_treasury_event(db: Session, event_id: int) -> EventReplayResult:
    event = db.get(TreasuryEvent, event_id)
    if event is None:
        raise ValueError("Treasury event not found")
    if event.processing_status not in {"FAILED", "QUARANTINED_SCHEMA", "QUARANTINED_EVENT_TYPE"}:
        raise ValueError("Only failed or schema/type-quarantined events can be replayed")
    if event.schema_version not in SUPPORTED_SCHEMA_VERSIONS or event.event_type not in SUPPORTED_EVENT_TYPES:
        raise ValueError("Event remains incompatible with the active schema/event registry")
    payload = json.loads(event.payload_json)
    event.replay_count += 1
    event.processing_error = ""
    try:
        projected, _ = _apply_event(db, event, payload)
        if not event.processing_status.startswith("QUARANTINED"):
            event.processing_status = "APPLIED" if projected else "ACCEPTED"
    except Exception as exc:
        projected = False
        event.processing_status = "FAILED"
        event.processing_error = str(exc)[:500]
    db.add(AuditLog(
        event_type="TREASURY_EVENT_REPLAY",
        actor="TREASURY_OPERATIONS",
        details=f"event_id={event.id}; replay_count={event.replay_count}; status={event.processing_status}",
    ))
    db.commit()
    return EventReplayResult(
        event_id=event.id,
        replay_count=event.replay_count,
        processing_status=event.processing_status,
        processing_error=event.processing_error,
        projected=projected,
    )


def list_treasury_events(db: Session, limit: int = 100) -> list[TreasuryEventOut]:
    rows = db.scalars(select(TreasuryEvent).order_by(TreasuryEvent.received_at.desc()).limit(limit)).all()
    return [_event_out(x) for x in rows]


def list_live_alerts(db: Session, status: str | None = None) -> list[LiveTreasuryAlertOut]:
    q = select(LiveTreasuryAlert)
    if status:
        q = q.where(LiveTreasuryAlert.status == status.upper())
    rows = db.scalars(q.order_by(LiveTreasuryAlert.severity, LiveTreasuryAlert.last_seen_at.desc())).all()
    return [_alert_out(x) for x in rows]


def acknowledge_live_alert(db: Session, alert_id: int, actor: str, comment: str = "") -> LiveTreasuryAlertOut:
    row = db.get(LiveTreasuryAlert, alert_id)
    if row is None:
        raise ValueError("Live treasury alert not found")
    row.status = "ACKNOWLEDGED"
    row.acknowledged_by = actor
    row.acknowledged_at = _now()
    db.add(AuditLog(
        event_type="LIVE_ALERT_ACKNOWLEDGED",
        actor=actor,
        details=f"alert_id={row.id}; key={row.alert_key}; comment={comment[:250]}",
    ))
    db.commit()
    return _alert_out(row)


def live_operations_status(db: Session) -> LiveOperationsStatusOut:
    cutoff = _now() - timedelta(hours=24)
    rows = db.scalars(select(TreasuryEvent).where(TreasuryEvent.received_at >= cutoff)).all()
    checkpoints = db.scalars(select(ConnectorCheckpoint).order_by(ConnectorCheckpoint.connector_name)).all()
    alert_rows = db.scalars(select(LiveTreasuryAlert).where(LiveTreasuryAlert.status.in_(["OPEN", "ACKNOWLEDGED"]))).all()
    lags = [max(0, int((x.received_at - x.event_time).total_seconds())) for x in rows]
    last_received = max((x.received_at for x in rows), default=None)
    warnings: list[str] = []
    quarantined = sum(1 for x in rows if x.processing_status.startswith("QUARANTINED"))
    failed = sum(1 for x in rows if x.processing_status == "FAILED")
    if quarantined:
        warnings.append(f"{quarantined} event(s) were quarantined in the last 24 hours.")
    if failed:
        warnings.append(f"{failed} event(s) failed projection in the last 24 hours.")
    if lags and max(lags) > settings.live_event_lag_warning_seconds:
        warnings.append("Observed event-arrival lag exceeded the configured live-operations tolerance.")
    critical = sum(1 for x in alert_rows if x.severity == "CRITICAL")
    status = "CRITICAL" if critical else "WATCH" if warnings or alert_rows else "NORMAL"
    return LiveOperationsStatusOut(
        status=status,
        events_24h=len(rows),
        applied_24h=sum(1 for x in rows if x.processing_status == "APPLIED"),
        quarantined_24h=quarantined,
        failed_24h=failed,
        duplicate_events=sum(x.duplicate_count for x in checkpoints),
        max_event_lag_seconds=max(lags) if lags else 0,
        open_alerts=len(alert_rows),
        critical_alerts=critical,
        last_event_received_at=last_received,
        checkpoints=[_checkpoint_out(x) for x in checkpoints],
        warnings=warnings,
    )


def run_live_monitor(db: Session) -> LiveMonitorRunOut:
    """Run deterministic continuous-monitor checks once.

    A production scheduler/event bus can invoke this function. It never sends payments or trades.
    """
    active_keys: set[str] = set()
    refreshed = 0
    notes: list[str] = []

    liquidity = calculate_global_liquidity(db)
    lar = calculate_liquidity_at_risk(db, simulations=500, seed=42)
    intraday = calculate_intraday_liquidity(db)

    for entity in liquidity.entities:
        if Decimal(entity.liquidity_headroom_reporting) < ZERO:
            key = f"LOCAL_LIQUIDITY_DEFICIT:{entity.entity_id}"
            active_keys.add(key)
            _upsert_alert(
                db,
                alert_key=key,
                category="LIQUIDITY",
                severity="CRITICAL",
                title=f"Local liquidity deficit: {entity.entity_name}",
                message=f"Entity liquidity headroom is {liquidity.reporting_currency} {entity.liquidity_headroom_reporting:,.2f}.",
            )
            refreshed += 1

    prob = Decimal(lar.probability_of_buffer_breach)
    if prob >= Decimal("0.05"):
        key = "LAR_BUFFER_BREACH_PROBABILITY"
        active_keys.add(key)
        _upsert_alert(
            db,
            alert_key=key,
            category="LIQUIDITY_AT_RISK",
            severity="HIGH" if prob < Decimal("0.15") else "CRITICAL",
            title="Liquidity-at-Risk tail warning",
            message=f"Modelled buffer-breach probability is {prob * 100:.2f}% over {lar.horizon_weeks} weeks; this is a scenario distribution, not a guaranteed forecast.",
        )
        refreshed += 1

    if Decimal(intraday.peak_intraday_funding_need) > ZERO:
        key = f"INTRADAY_FUNDING:{intraday.entity_id}"
        active_keys.add(key)
        _upsert_alert(
            db,
            alert_key=key,
            category="INTRADAY_LIQUIDITY",
            severity="HIGH",
            title="Intraday funding requirement detected",
            message=f"Peak intraday funding need is {intraday.reporting_currency} {intraday.peak_intraday_funding_need:,.2f} for {intraday.entity_name}.",
        )
        refreshed += 1

    health = {x.connector_name: x for x in connector_health(db)}
    checkpoints = db.scalars(select(ConnectorCheckpoint)).all()
    for cp in checkpoints:
        h = health.get(cp.connector_name)
        if h and not h.execution_usable:
            key = f"CONNECTOR_STALE:{cp.connector_name}"
            active_keys.add(key)
            _upsert_alert(
                db,
                alert_key=key,
                category="DATA_FRESHNESS",
                severity="HIGH" if h.required_for_execution else "MEDIUM",
                title=f"Connector stale: {cp.connector_name}",
                message=f"Connector is not execution-usable; age={h.age_minutes} minutes, status={h.status}.",
            )
            refreshed += 1

    recent_failures = db.scalars(
        select(TreasuryEvent).where(
            TreasuryEvent.received_at >= _now() - timedelta(hours=1),
            TreasuryEvent.processing_status.in_(["FAILED", "QUARANTINED_SCHEMA", "QUARANTINED_EVENT_TYPE", "QUARANTINED_SEQUENCE", "QUARANTINED_OUT_OF_ORDER"]),
        )
    ).all()
    if recent_failures:
        key = "LIVE_EVENT_PROCESSING_EXCEPTIONS"
        active_keys.add(key)
        _upsert_alert(
            db,
            alert_key=key,
            category="DATA_QUALITY",
            severity="MEDIUM",
            title="Live event processing exceptions",
            message=f"{len(recent_failures)} failed/quarantined event(s) were observed in the last hour.",
        )
        refreshed += 1

    # Resolve only monitor-generated conditions that are no longer active. Acknowledged alerts are
    # retained as evidence but can become resolved when the underlying condition clears.
    monitor_prefixes = ("LOCAL_LIQUIDITY_DEFICIT:", "LAR_BUFFER_BREACH_PROBABILITY", "INTRADAY_FUNDING:", "CONNECTOR_STALE:", "LIVE_EVENT_PROCESSING_EXCEPTIONS")
    for row in db.scalars(select(LiveTreasuryAlert).where(LiveTreasuryAlert.status.in_(["OPEN", "ACKNOWLEDGED"]))).all():
        if row.alert_key.startswith(monitor_prefixes) and row.alert_key not in active_keys:
            row.status = "RESOLVED"
            row.last_seen_at = _now()

    db.add(AuditLog(
        event_type="LIVE_TREASURY_MONITOR_RUN",
        actor="AUTONOMOUS_MONITOR",
        details=(
            f"alerts_refreshed={refreshed}; headroom={liquidity.liquidity_headroom}; "
            f"lar_breach_probability={lar.probability_of_buffer_breach}; intraday_need={intraday.peak_intraday_funding_need}"
        ),
    ))
    db.commit()

    alert_rows = db.scalars(select(LiveTreasuryAlert).where(LiveTreasuryAlert.status.in_(["OPEN", "ACKNOWLEDGED"]))).all()
    critical = sum(1 for x in alert_rows if x.severity == "CRITICAL")
    status = "CRITICAL" if critical else "WATCH" if alert_rows else "NORMAL"
    notes.append("Monitor is advisory/control-only and cannot create or release treasury transactions.")
    return LiveMonitorRunOut(
        status=status,
        alerts_created_or_refreshed=refreshed,
        open_alerts=len(alert_rows),
        critical_alerts=critical,
        liquidity_headroom=liquidity.liquidity_headroom,
        lar_buffer_breach_probability=lar.probability_of_buffer_breach,
        intraday_peak_funding_need=intraday.peak_intraday_funding_need,
        notes=notes,
    )


def _sign_payload(payload_json: str) -> str:
    secret = settings.execution_signing_secret
    if not secret:
        if settings.environment.lower() == "production":
            raise ValueError("Execution signing secret is required in production")
        return "DEMO_UNVERIFIED"
    return hmac.new(secret.encode("utf-8"), payload_json.encode("utf-8"), hashlib.sha256).hexdigest()


def create_execution_message(
    db: Session,
    proposal_id: int,
    connector_name: str,
    idempotency_key: str,
    actor: str,
) -> ExecutionMessageOut:
    if settings.environment.lower() == "production":
        from app.services.production import require_live_release
        require_live_release(db)
    existing = db.scalar(select(ExecutionMessage).where(ExecutionMessage.idempotency_key == idempotency_key))
    if existing:
        if existing.proposal_id != proposal_id or existing.connector_name != connector_name:
            raise ValueError("Idempotency key collision: execution key already belongs to another proposal or connector")
        return _execution_out(existing)

    user = db.scalar(select(UserAccount).where(UserAccount.username == actor, UserAccount.active.is_(True)))
    if user is None or user.role not in {"PAYMENT_OPERATOR", "GROUP_TREASURER"}:
        raise PermissionError("Only an authorized payment operator or group treasurer can create an execution message")

    proposal = db.get(TransactionProposal, proposal_id)
    if proposal is None:
        raise ValueError("Transaction proposal not found")
    if proposal.status != "RELEASED_FOR_EXECUTION":
        raise ValueError("Proposal must be RELEASED_FOR_EXECUTION before an external execution message can be created")

    health = {x.connector_name: x for x in connector_health(db)}
    selected = health.get(connector_name)
    if selected is None or not selected.execution_usable:
        raise ValueError("Selected execution connector is unavailable or stale")
    connector = db.scalar(select(SourceConnector).where(SourceConnector.connector_name == connector_name))
    if connector is None or connector.connector_type != "BANK":
        raise ValueError("Execution connector must be an approved BANK connector")

    message_id = f"TX-{uuid.uuid4().hex[:20].upper()}"
    payload = {
        "message_id": message_id,
        "proposal_id": proposal.id,
        "proposal_type": proposal.proposal_type,
        "source_entity_id": proposal.source_entity_id,
        "target_entity_id": proposal.target_entity_id,
        "counterparty": proposal.counterparty,
        "currency": proposal.currency,
        "amount": str(proposal.amount),
        "purpose": proposal.purpose,
        "underlying_reference": proposal.underlying_reference,
        "released_at": proposal.executed_at.isoformat() if proposal.executed_at else None,
        "schema_version": "1.0",
    }
    payload_json = _canonical_json(payload)
    row = ExecutionMessage(
        message_id=message_id,
        proposal_id=proposal.id,
        connector_name=connector_name,
        idempotency_key=idempotency_key,
        payload_hash=_hash(payload_json),
        payload_json=payload_json,
        signature=_sign_payload(payload_json),
        status="QUEUED",
        created_by=actor,
    )
    db.add(row)
    observe_execution_message("QUEUED")
    db.add(AuditLog(
        event_type="EXECUTION_MESSAGE_CREATED",
        actor=actor,
        details=f"proposal_id={proposal.id}; message_id={message_id}; connector={connector_name}",
    ))
    db.commit()
    db.refresh(row)
    return _execution_out(row)


def list_execution_messages(db: Session, status: str | None = None) -> list[ExecutionMessageOut]:
    q = select(ExecutionMessage)
    if status:
        q = q.where(ExecutionMessage.status == status.upper())
    rows = db.scalars(q.order_by(ExecutionMessage.created_at.desc())).all()
    return [_execution_out(x) for x in rows]


def mark_execution_message_sent(db: Session, message_id: str, connector_name: str) -> ExecutionMessageOut:
    if settings.environment.lower() == "production":
        from app.services.production import require_live_release
        require_live_release(db)
    row = db.scalar(select(ExecutionMessage).where(ExecutionMessage.message_id == message_id))
    if row is None:
        raise ValueError("Execution message not found")
    if row.connector_name != connector_name:
        raise PermissionError("Connector identity does not match the execution message route")
    if row.status == "SENT":
        return _execution_out(row)
    if row.status != "QUEUED":
        raise ValueError(f"Execution message cannot be sent from status {row.status}")
    row.status = "SENT"
    row.sent_at = _now()
    observe_execution_message("SENT")
    db.add(AuditLog(
        event_type="EXECUTION_MESSAGE_DISPATCHED",
        actor=connector_name,
        details=f"message_id={row.message_id}; proposal_id={row.proposal_id}",
    ))
    db.commit()
    return _execution_out(row)


def acknowledge_execution_message(
    db: Session,
    message_id: str,
    connector_name: str,
    status: str,
    external_reference: str | None,
    detail: str,
) -> ExecutionMessageOut:
    row = db.scalar(select(ExecutionMessage).where(ExecutionMessage.message_id == message_id))
    if row is None:
        raise ValueError("Execution message not found")
    if row.connector_name != connector_name:
        raise PermissionError("Connector identity does not match the execution message route")
    normalized = status.upper()
    if normalized not in {"ACKNOWLEDGED", "REJECTED"}:
        raise ValueError("status must be ACKNOWLEDGED or REJECTED")
    if row.status not in {"SENT", normalized}:
        raise ValueError(f"Execution acknowledgement cannot be applied from status {row.status}")
    row.status = normalized
    row.acknowledged_at = _now()
    row.external_reference = external_reference
    row.acknowledgement_detail = detail[:500]
    observe_execution_message(normalized)
    db.add(AuditLog(
        event_type="EXECUTION_MESSAGE_ACKNOWLEDGED",
        actor=connector_name,
        details=f"message_id={row.message_id}; status={normalized}; external_reference={external_reference or ''}",
    ))
    db.commit()
    return _execution_out(row)
