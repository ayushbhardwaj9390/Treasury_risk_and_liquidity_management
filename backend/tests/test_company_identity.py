"""Account identity is read from active enterprise records, never client-selected roles."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.db import Base, get_db
from app.main import app
from app.models import UserAccount, SourceConnector


@pytest.fixture
def client(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add_all([UserAccount(username="reviewer", display_name="Reviewer", role="RISK_MANAGER", active=True),
                    UserAccount(username="disabled", display_name="Disabled", role="CFO", active=False),
                    SourceConnector(connector_name="BANK_SERVICE", connector_type="BANK", system_name="Test only", status="ACTIVE")])
        db.commit()
    def database():
        with Session(engine) as db:
            yield db
    monkeypatch.setattr(settings, "environment", "development")
    monkeypatch.setattr(settings, "auth_mode", "demo_header")
    monkeypatch.setattr("app.main.SessionLocal", lambda: Session(engine))
    app.dependency_overrides[get_db] = database
    yield TestClient(app)
    app.dependency_overrides.pop(get_db)
    engine.dispose()


def test_identity_requires_authentication(client):
    assert client.get("/api/v1/production/identity").status_code == 401


@pytest.mark.parametrize("username", ["disabled", "unregistered"])
def test_identity_rejects_inactive_or_unregistered_account(client, username):
    assert client.get("/api/v1/production/identity", headers={"X-Treasury-User": username}).status_code == 403


def test_identity_uses_database_role_not_request_role(client):
    response = client.get("/api/v1/production/identity", headers={"X-Treasury-User": "reviewer", "X-Treasury-Role": "CFO"})
    assert response.json() == {"username": "reviewer", "role": "RISK_MANAGER", "active": True}


def test_production_analysis_rejects_signed_but_disabled_account(client, monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr("app.core.security.treasury_identity", lambda *args: "disabled")
    response = client.get("/api/v1/liquidity/global", headers={"Authorization": "Bearer verified-in-test"})
    assert response.status_code == 403


@pytest.mark.parametrize("subject,path,status", [
    ("BANK_SERVICE", "/api/v1/integrations/phase1/bank/balances", 422),
    ("UNKNOWN", "/api/v1/integrations/phase1/bank/balances", 403),
    ("BANK_SERVICE", "/api/v1/integrations/phase1/erp/cash-flows", 403),
])
def test_registered_connector_is_bound_to_source_type(client, monkeypatch, subject, path, status):
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr("app.core.security._verified_connector_identity", lambda authorization: subject)
    assert client.post(path, json={}, headers={"Authorization": "Bearer verified-in-test"}).status_code == status
