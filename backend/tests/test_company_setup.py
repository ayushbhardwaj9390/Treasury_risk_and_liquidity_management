import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from app.core.config import settings
from app.core.db import Base, get_db
from app.main import app
from app.models import AuditLog, LegalEntity, UserAccount


@pytest.fixture
def company_client(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add_all([UserAccount(username=name, display_name=name, role=role, active=active)
            for name, role, active in [("owner", "GROUP_TREASURER", True), ("reader", "VIEWER", True),
                ("disabled", "GROUP_TREASURER", False)]])
        db.commit()
    def database():
        with Session(engine) as db:
            yield db
    monkeypatch.setattr(settings, "environment", "development")
    monkeypatch.setattr(settings, "auth_mode", "demo_header")
    app.dependency_overrides[get_db] = database
    yield TestClient(app), engine
    app.dependency_overrides.pop(get_db)
    engine.dispose()


PROFILE = {"company_name": "Example Manufacturing", "industry": "MANUFACTURING", "country_code": "IN", "expected_version": 0}
ENTITY = {"name": "Example India Ltd", "country_code": "IN", "functional_currency": "INR"}


def submit(client, path, payload, user="owner"):
    return client.post(f"/api/v1/company/{path}", json=payload, headers={"X-Treasury-User": user})


def test_setup_requires_active_authenticated_identity(company_client):
    client, _ = company_client
    assert client.get("/api/v1/company/setup").status_code == 401
    for user in ("disabled", "unknown"):
        assert client.get("/api/v1/company/setup", headers={"X-Treasury-User": user}).status_code == 403
    assert submit(client, "profile", PROFILE, "reader").status_code == 403
    assert submit(client, "entities", ENTITY, "reader").status_code == 403


def test_profile_persistence_revision_and_audit(company_client):
    client, engine = company_client
    assert submit(client, "profile", PROFILE).json()["profile"]["version"] == 1
    assert submit(client, "profile", PROFILE).status_code == 409
    updated = {**PROFILE, "company_name": "Example Services", "industry": "SERVICES", "expected_version": 1}
    assert submit(client, "profile", updated).json()["profile"]["version"] == 2
    assert submit(client, "profile", updated).status_code == 409
    result = client.get("/api/v1/company/setup", headers={"X-Treasury-User": "reader"}).json()
    assert result["profile"]["company_name"] == "Example Services"
    assert result["can_edit"] is False
    assert result["reporting_currency"] == settings.group_reporting_currency
    with Session(engine) as db:
        logs = db.scalars(select(AuditLog)).all()
        assert len(logs) == 2 and all(log.actor == "owner" for log in logs)


def test_registration_is_pending_and_does_not_change_engine(company_client):
    client, engine = company_client
    assert submit(client, "entities", ENTITY).status_code == 409
    assert submit(client, "profile", PROFILE).status_code == 200
    result = submit(client, "entities", ENTITY)
    assert result.status_code == 200
    assert result.json()["registrations"][0]["status"] == "PENDING_REVIEW"
    assert submit(client, "entities", {**ENTITY, "name": "example india ltd"}).status_code == 409
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(LegalEntity)) == 0
        assert db.scalar(select(func.count()).select_from(AuditLog)) == 2


@pytest.mark.parametrize("change", [{"country_code": "India"}, {"company_name": "  "},
    {"industry": "UNREVIEWED"}, {"reporting_currency": "INR"}, {"expected_version": -1}])
def test_profile_rejects_invalid_or_policy_fields(company_client, change):
    assert submit(company_client[0], "profile", {**PROFILE, **change}).status_code == 422
