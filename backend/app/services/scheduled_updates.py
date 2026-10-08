from datetime import UTC, datetime, timedelta
from sqlalchemy import select, update
from app.models import AuditLog, ConnectorCheckpoint, SourceAuthorityPolicy, SourceConnector
from app.models.scheduled_updates import ScheduledUpdate
from app.services.enterprise_controls import _user
from app.services.production import actor_role


def now():
    return datetime.now(UTC).replace(tzinfo=None)


def freshness(last_success, current, stale_after_minutes):
    if last_success is None:
        return "MISSING"
    if last_success > current:
        return "INVALID_TIMESTAMP"
    return "STALE" if current - last_success >= timedelta(minutes=stale_after_minutes) else "RECENT"


def list_schedules(db, actor):
    user = _user(db, actor)
    current = now()
    schedules = {row.connector_id: row for row in db.scalars(select(ScheduledUpdate))}
    checkpoints = {row.connector_name: row for row in db.scalars(select(ConnectorCheckpoint))}
    rows = []
    for connector in db.scalars(select(SourceConnector).order_by(SourceConnector.id)):
        schedule = schedules.get(connector.id)
        checkpoint = checkpoints.get(connector.connector_name)
        # The connector registration's default success timestamp is not collection evidence.
        observed = checkpoint.last_event_time if checkpoint and checkpoint.accepted_count > 0 else None
        policies = db.scalars(select(SourceAuthorityPolicy).where(
            SourceAuthorityPolicy.connector_code == connector.connector_name)).all()
        rows.append({"connector_id": connector.id, "connector_name": connector.connector_name,
            "connector_status": connector.status,
            "authority": [{"domain": p.data_domain, "mode": p.mode} for p in policies],
            "interval_minutes": schedule.interval_minutes if schedule else 60,
            "stale_after_minutes": schedule.stale_after_minutes if schedule else 120,
            "enabled": bool(schedule and schedule.enabled), "version": schedule.version if schedule else 0,
            "next_due_at": schedule.next_due_at if schedule else None,
            "due": bool(schedule and schedule.enabled and schedule.next_due_at <= current),
            "last_success_at": observed,
            "freshness": freshness(observed, current, schedule.stale_after_minutes if schedule else 120),
            "last_attempt_at": schedule.last_attempt_at if schedule else None,
            "last_attempt_status": schedule.last_attempt_status if schedule else "NOT_ATTEMPTED",
            "last_attempt_reason": schedule.last_attempt_reason if schedule else "No worker attempt recorded."})
    return {"can_edit": user.role == "GROUP_TREASURER", "worker_status": "BLOCKED",
        "worker_reason": "A credential-backed, approved collection worker is not configured.",
        "freshness_basis": "Connector checkpoint accepted event time; not domain coverage or certification.",
        "schedules": rows}


def save_schedule(db, request, actor):
    actor_role(db, actor, {"GROUP_TREASURER"})
    connector = db.get(SourceConnector, request.connector_id)
    if connector is None:
        raise LookupError("Register the connector before creating a schedule.")
    if request.enabled and connector.status != "ACTIVE":
        raise ValueError("The registered connector is not active; leave its schedule paused.")
    values = {"interval_minutes": request.interval_minutes, "stale_after_minutes": request.stale_after_minutes,
        "enabled": request.enabled, "next_due_at": now()}
    if request.expected_version == 0:
        db.add(ScheduledUpdate(connector_id=connector.id, **values))
    else:
        result = db.execute(update(ScheduledUpdate).where(ScheduledUpdate.connector_id == connector.id,
            ScheduledUpdate.version == request.expected_version).values(**values, version=request.expected_version + 1))
        if result.rowcount != 1:
            raise ValueError("Schedule changed. Reload before saving.")
    db.add(AuditLog(event_type="UPDATE_SCHEDULE_SAVED", actor=actor,
        details=f"Connector {connector.id}; revision {request.expected_version + 1}; collection only, worker blocked"))
    db.commit()
    return list_schedules(db, actor)


def record_due_attempts(db, actor):
    """Operator-run readiness probe. No arbitrary adapters, network calls or success writes."""
    actor_role(db, actor, {"GROUP_TREASURER"})
    current, outcomes = now(), []
    due = db.scalars(select(ScheduledUpdate).where(ScheduledUpdate.enabled.is_(True),
        ScheduledUpdate.next_due_at <= current).order_by(ScheduledUpdate.id).limit(100)).all()
    for row in due:
        connector = db.get(SourceConnector, row.connector_id)
        reason = "Approved collection adapter and credentials are not configured. No data was collected."
        if not connector or connector.status != "ACTIVE":
            reason = "Connector registration is missing or inactive. No data was collected."
        changed = db.execute(update(ScheduledUpdate).where(ScheduledUpdate.id == row.id,
            ScheduledUpdate.version == row.version, ScheduledUpdate.next_due_at <= current,
            ScheduledUpdate.enabled.is_(True)).values(version=row.version + 1,
            next_due_at=current + timedelta(minutes=row.interval_minutes), last_attempt_at=current,
            last_attempt_status="BLOCKED", last_attempt_reason=reason))
        if changed.rowcount != 1:
            continue
        db.add(AuditLog(event_type="UPDATE_SCHEDULE_BLOCKED", actor=actor,
            details=f"Schedule {row.id}; {reason}"))
        outcomes.append({"connector_id": row.connector_id, "status": "BLOCKED", "reason": reason})
    db.commit()
    return outcomes
