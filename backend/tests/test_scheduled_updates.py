from datetime import datetime, timedelta
import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.core.db import Base
from app.models import AuditLog, ConnectorCheckpoint, SourceAuthorityPolicy, SourceConnector, UserAccount
from app.models.scheduled_updates import ScheduledUpdate
from app.schemas.scheduled_updates import ScheduleSave
from app.services import scheduled_updates as service


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add_all([UserAccount(username="owner", display_name="Owner", role="GROUP_TREASURER", active=True),
            UserAccount(username="reader", display_name="Reader", role="VIEWER", active=True),
            UserAccount(username="disabled", display_name="Disabled", role="GROUP_TREASURER", active=False)])
        session.add(SourceConnector(id=1, connector_name="DUMMY_BANK", connector_type="BANK", system_name="Dummy", status="ACTIVE"))
        session.add(SourceAuthorityPolicy(connector_code="DUMMY_BANK", data_domain="BANK_BALANCES", mode="SHADOW"))
        session.commit()
        yield session
    engine.dispose()


def request(**changes):
    return ScheduleSave(**{"connector_id": 1, "interval_minutes": 60, "stale_after_minutes": 120,
        "enabled": True, "expected_version": 0, **changes})


@pytest.mark.parametrize("changes", [{"interval_minutes": 4}, {"interval_minutes": 10081},
    {"interval_minutes": 5.5}, {"stale_after_minutes": 59}, {"stale_after_minutes": 20161},
    {"url": "https://unapproved.example"}, {"enabled": "true"}])
def test_bounds(changes):
    with pytest.raises(ValidationError):
        request(**changes)


def test_missing_data_and_roles(db):
    for actor in ("disabled", "unknown"):
        with pytest.raises(PermissionError):
            service.list_schedules(db, actor)
    with pytest.raises(PermissionError):
        service.save_schedule(db, request(), "reader")
    initial = service.list_schedules(db, "reader")
    assert initial["can_edit"] is False
    assert initial["schedules"][0]["freshness"] == "MISSING"
    assert initial["schedules"][0]["last_success_at"] is None
    assert initial["worker_status"] == "BLOCKED"


def test_cas_and_unregistered_inactive_connectors(db):
    with pytest.raises(LookupError):
        service.save_schedule(db, request(connector_id=999), "owner")
    assert service.save_schedule(db, request(), "owner")["schedules"][0]["version"] == 1
    with pytest.raises(IntegrityError):
        service.save_schedule(db, request(), "owner")
    db.rollback()
    with pytest.raises(ValueError, match="changed"):
        service.save_schedule(db, request(expected_version=2), "owner")
    db.get(SourceConnector, 1).status = "BLOCKED"
    db.flush()
    with pytest.raises(ValueError, match="not active"):
        service.save_schedule(db, request(expected_version=1), "owner")
    result = service.save_schedule(db, request(expected_version=1, enabled=False), "owner")
    assert result["schedules"][0]["version"] == 2
    assert result["schedules"][0]["enabled"] is False


def test_due_attempts_never_fake_success_and_repeat_is_not_due(db):
    service.save_schedule(db, request(), "owner")
    assert service.record_due_attempts(db, "owner")[0]["status"] == "BLOCKED"
    assert service.record_due_attempts(db, "owner") == []
    row = db.scalar(select(ScheduledUpdate))
    assert row.version == 2 and row.last_attempt_at is not None
    assert row.next_due_at > row.last_attempt_at
    result = service.list_schedules(db, "reader")["schedules"][0]
    assert result["last_success_at"] is None and result["freshness"] == "MISSING"
    assert db.scalar(select(SourceAuthorityPolicy)).mode == "SHADOW"
    assert len(db.scalars(select(AuditLog)).all()) == 2
    with pytest.raises(PermissionError):
        service.record_due_attempts(db, "reader")


def test_checkpoint_freshness_is_not_seed_success(db):
    old = service.now() - timedelta(hours=3)
    db.add(ConnectorCheckpoint(connector_name="DUMMY_BANK", source_system="Dummy", accepted_count=1, last_event_time=old))
    db.commit()
    assert service.list_schedules(db, "reader")["schedules"][0]["freshness"] == "STALE"
    current = datetime(2026, 10, 8)
    assert service.freshness(None, current, 60) == "MISSING"
    assert service.freshness(current + timedelta(seconds=1), current, 60) == "INVALID_TIMESTAMP"
    assert service.freshness(current - timedelta(minutes=59), current, 60) == "RECENT"
    assert service.freshness(current - timedelta(minutes=60), current, 60) == "STALE"
