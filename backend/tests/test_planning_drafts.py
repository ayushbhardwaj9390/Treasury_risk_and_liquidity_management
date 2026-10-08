from copy import deepcopy
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from app.api.planning_drafts import router
from app.core.config import settings
from app.core.db import Base, get_db
from app.models import AuditLog, CashFlow, UserAccount

PATH = "/api/v1/company/planning-draft"
PLAN = {"expected_version": 0, "flows": [{"id": "receipt-1", "entity": "Fictional company", "date": "2026-10-12",
    "direction": "INFLOW", "currency": "USD", "amount": "1500.00", "category": "OTHER", "probability": "1"}],
    "assumptions": {"start": "2026-10-12", "weeks": 2, "opening": "1000", "buffer": "800", "rates": {},
        "delay": 0, "receipts": 0, "costs": 0, "oil": 0, "fx": 0}}


@pytest.fixture
def client_db(monkeypatch):
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
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = database
    yield TestClient(app), engine
    engine.dispose()


def save(client, payload, actor="owner"):
    return client.put(PATH, json=payload, headers={"X-Treasury-User": actor})


def test_authenticated_role_boundaries(client_db):
    client, _ = client_db
    assert client.get(PATH).status_code == 401
    assert client.put(PATH, json=PLAN).status_code == 401
    for actor in ("unknown", "disabled"):
        assert client.get(PATH, headers={"X-Treasury-User": actor}).status_code == 403
        assert save(client, PLAN, actor).status_code == 403
    assert save(client, PLAN, "reader").status_code == 403
    assert client.get(PATH, headers={"X-Treasury-User": "reader"}).json() == {"draft": None, "can_edit": False}


def test_persistence_versions_audit_and_no_engine_writes(client_db):
    client, engine = client_db
    first = save(client, PLAN)
    assert first.status_code == 200
    assert first.json()["draft"]["version"] == 1
    assert save(client, PLAN).status_code == 409
    changed = deepcopy(PLAN)
    changed["expected_version"] = 1
    changed["assumptions"]["delay"] = 10
    assert save(client, changed).json()["draft"]["version"] == 2
    assert save(client, changed).status_code == 409
    result = client.get(PATH, headers={"X-Treasury-User": "reader"}).json()
    assert result["draft"]["flows"] == PLAN["flows"]
    assert result["draft"]["assumptions"]["delay"] == 10
    assert result["draft"]["updated_by"] == "owner"
    assert result["draft"]["updated_at"].endswith("Z")
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(CashFlow)) == 0
        logs = db.scalars(select(AuditLog)).all()
        assert len(logs) == 2
        assert all(log.event_type == "PLANNING_DRAFT_SAVED" and log.actor == "owner" for log in logs)
        assert all("Fictional company" not in log.details and "1500" not in log.details for log in logs)


@pytest.mark.parametrize("field,value", [("weeks", 53), ("weeks", True), ("delay", -1),
    ("start", "2026-02-30"), ("opening", "1e6"), ("fx", 0.05), ("rates", {"EUR": "NaN"}),
    ("rates", {"USD": "2"}), ("rates", {"BAD": "1"})])
def test_invalid_assumptions(client_db, field, value):
    plan = deepcopy(PLAN)
    plan["assumptions"][field] = value
    assert save(client_db[0], plan).status_code == 422


@pytest.mark.parametrize("field,value", [("amount", "0"), ("amount", "1000000000001"),
    ("currency", "EUR"), ("probability", "1.1"), ("date", "2026-02-30"), ("id", "=formula"),
    ("category", "CRUDE_PURCHASE"), ("entity", "x" * 121)])
def test_invalid_flows(client_db, field, value):
    plan = deepcopy(PLAN)
    plan["flows"][0][field] = value
    assert save(client_db[0], plan).status_code == 422


def test_duplicate_limits_unknown_fields_and_multicurrency(client_db):
    client, _ = client_db
    for flows in ([], PLAN["flows"] * 2, PLAN["flows"] * 501):
        assert save(client, {**PLAN, "flows": flows}).status_code == 422
    assert save(client, {**PLAN, "source_authority": "ACTIVE"}).status_code == 422
    assert save(client, {**PLAN, "expected_version": -1}).status_code == 422
    plan = deepcopy(PLAN)
    plan["flows"][0]["currency"] = "EUR"
    plan["assumptions"]["rates"] = {"EUR": "1.10"}
    assert save(client, plan).status_code == 200
