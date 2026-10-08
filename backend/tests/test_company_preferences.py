import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.core.db import Base
from app.models import AuditLog, UserAccount, LegalEntity
from app.models.company_preferences import CompanyPreferences
from app.schemas.company_preferences import PreferencesSave
from app.services.company_preferences import read_preferences, save_preferences

VALUES = {"countries": ["US", "IN"], "currencies": ["USD", "INR"], "minimum_cash_usd": "1000.50", "reviewer_roles": ["GROUP_TREASURER", "RISK_MANAGER"], "expected_version": 0}


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add_all([UserAccount(username=name, display_name=name, role=role, active=active)
            for name, role, active in [("owner", "GROUP_TREASURER", True), ("reader", "VIEWER", True), ("disabled", "GROUP_TREASURER", False)]])
        session.commit()
        yield session
    engine.dispose()


def test_permissions_persistence_and_optimistic_version(db):
    request = PreferencesSave(**VALUES)
    for actor in ("reader", "disabled", "unknown"):
        with pytest.raises(PermissionError):
            save_preferences(db, request, actor)
    for actor in ("disabled", "unknown"):
        with pytest.raises(PermissionError):
            read_preferences(db, actor)
    saved = save_preferences(db, request, "owner")
    assert saved["status"] == "DRAFT_NOT_ACTIVATED"
    assert saved["draft"]["version"] == 1
    assert read_preferences(db, "reader")["can_edit"] is False
    with pytest.raises(IntegrityError):
        save_preferences(db, request, "owner")
    db.rollback()
    update = PreferencesSave(**{**VALUES, "expected_version": 1, "minimum_cash_usd": "2000"})
    assert save_preferences(db, update, "owner")["draft"]["version"] == 2
    with pytest.raises(ValueError, match="changed"):
        save_preferences(db, update, "owner")
    db.rollback()
    logs = db.scalars(select(AuditLog)).all()
    assert len(logs) == 2
    assert all(log.event_type == "COMPANY_PREFERENCES_SAVED" for log in logs)
    assert db.scalars(select(LegalEntity)).all() == []
    assert db.scalar(select(UserAccount).where(UserAccount.username == "reader")).role == "VIEWER"


@pytest.mark.parametrize("change", [{"countries": ["ZZ"]}, {"countries": ["US", "US"]}, {"currencies": []}, {"currencies": ["BTC"]}, {"reviewer_roles": ["ADMIN"]}, {"minimum_cash_usd": "-1"}, {"minimum_cash_usd": "1.001"}, {"minimum_cash_usd": "1000000000000"}, {"minimum_cash_usd": "NaN"}, {"minimum_cash_usd": 100}, {"expected_version": True}, {"activate": True}, {"reporting_currency": "EUR"}])
def test_rejects_invalid_or_authoritative_fields(change):
    with pytest.raises(ValidationError):
        PreferencesSave(**{**VALUES, **change})
