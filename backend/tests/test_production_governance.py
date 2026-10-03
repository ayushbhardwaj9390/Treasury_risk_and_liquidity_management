"""Synthetic control tests; none of these are enterprise certification evidence."""
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.db import Base, get_db
from app.core.config import settings
from app.main import app
from app.models import UserAccount, ModelRegistryEntry
from app.models.production import ProductionEvidence, ProductionRelease, ProductionSignoff
from app.schemas.production import ReleaseCreate, EvidenceCreate, ObservationCreate, SignoffCreate, TransitionCreate, BenchmarkCreate
from app.services import production as p


@pytest.fixture
def db(monkeypatch):
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        roles = p.SIGNOFF_ROLES | {"TREASURY_ANALYST", "VIEWER"}
        for role in roles:
            session.add(UserAccount(username=role, display_name=role, role=role, active=True))
        session.add(UserAccount(username="maker", display_name="maker", role="GROUP_TREASURER", active=True))
        session.add(ModelRegistryEntry(model_code="FORECAST", version="1", model_type="deterministic"))
        session.commit()
        monkeypatch.setattr(p, "parallel_readiness", lambda db: type("Ready", (), {"status": "READY_FOR_CONTROLLED_PROMOTION"})())
        yield session
    engine.dispose()


def candidate(db):
    return p.create_release(db, ReleaseCreate(name="test", artifact_sha256="a" * 64,
                            previous_artifact_sha256="b" * 64), "maker")["id"]


def evidence(gate, kind="REAL", result="PASS"):
    return EvidenceCreate(gate=gate, kind=kind, result=result, document_sha256="c" * 64,
                          reference="test evidence only", scope="GROUP", expires_at=datetime.now(UTC) + timedelta(days=7),
                          details={"model_version": "1", "developer": "developer", "benchmark_sha256": "d" * 64,
                                   "limitations": "test", "models": {"FORECAST": "1"}, "rto_seconds": 10, "rpo_seconds": 0,
                                   "cases": [{"id": "case-1", "expected": "blocked early execution", "actual": "blocked",
                                              "result": "PASS", "document_sha256": "f" * 64}], "open_material_defects": 0})


def populate(db, rid, metric_lag=None):
    for gate, role in p.GATES.items():
        p.add_evidence(db, rid, evidence(gate), role)
    for offset in range(60):
        for metric in p.METRICS:
            p.add_observation(db, rid, ObservationCreate(day=date.today() - timedelta(days=offset + (metric_lag or {}).get(metric, 0)),
                metric=metric, scope="GROUP", kind="REAL", incumbent=100, platform=100,
                document_sha256="e" * 64), "TREASURY_ANALYST")


def approve(db, rid):
    digest = p.snapshot(db, rid)["evidence_digest"]
    for role in sorted(p.SIGNOFF_ROLES):
        p.signoff(db, rid, SignoffCreate(evidence_digest=digest, decision="APPROVE", reason="test only"), role)


def test_default_release_is_blocked(db):
    status = p.snapshot(db, candidate(db))
    assert status["status"] == "BLOCKED"
    assert any("BANK_UAT" in b for b in status["blockers"])
    assert status["autonomous_execution"] is False


def test_synthetic_evidence_never_qualifies(db):
    rid = candidate(db)
    p.add_evidence(db, rid, evidence("BANK_UAT", "SYNTHETIC"), "INTEGRATION_OWNER")
    assert any("BANK_UAT" in b for b in p.snapshot(db, rid)["blockers"])


def test_rbac_and_independence(db):
    rid = candidate(db)
    with pytest.raises(PermissionError):
        p.add_evidence(db, rid, evidence("BANK_UAT"), "VIEWER")
    request = evidence("MODEL_VALIDATION")
    request.details["developer"] = "RISK_MANAGER"
    with pytest.raises(ValueError):
        p.add_evidence(db, rid, request, "RISK_MANAGER")
    with pytest.raises(PermissionError):
        p.signoff(db, rid, SignoffCreate(evidence_digest=p.snapshot(db, rid)["evidence_digest"],
                                        decision="APPROVE", reason="self"), "maker")


def test_future_zero_baseline_and_duplicate_observations(db):
    rid = candidate(db)
    request = ObservationCreate(day=date.today(), metric="CASH", scope="GROUP", kind="REAL",
                                incumbent=0, platform=1, document_sha256="e" * 64)
    assert p.add_observation(db, rid, request, "TREASURY_ANALYST")["material"]
    request.day = date.today() + timedelta(days=1)
    with pytest.raises(ValueError):
        p.add_observation(db, rid, request, "TREASURY_ANALYST")


def test_no_early_approval_or_go_live(db):
    rid = candidate(db)
    with pytest.raises(ValueError):
        p.signoff(db, rid, SignoffCreate(evidence_digest=p.snapshot(db, rid)["evidence_digest"],
                                        decision="APPROVE", reason="early"), "CFO")
    p.transition(db, rid, TransitionCreate(action="START_PARALLEL", reason="test"), "maker")
    with pytest.raises(ValueError):
        p.transition(db, rid, TransitionCreate(action="GO_LIVE", reason="early"), "GROUP_TREASURER")


def test_full_governance_rollback_and_frozen_evidence(db, monkeypatch):
    rid = candidate(db)
    populate(db, rid)
    approve(db, rid)
    p.transition(db, rid, TransitionCreate(action="START_PARALLEL", reason="test"), "maker")
    assert p.transition(db, rid, TransitionCreate(action="GO_LIVE", reason="test only"), "GROUP_TREASURER")["state"] == "LIVE"
    monkeypatch.setattr(settings, "production_release_id", rid)
    p.require_live_release(db)
    with pytest.raises(ValueError):
        p.add_evidence(db, rid, evidence("BANK_UAT"), "INTEGRATION_OWNER")
    result = p.transition(db, rid, TransitionCreate(action="ROLLBACK", reason="test"), "OPERATIONS_MANAGER")
    assert result["deployment_performed"] is False
    assert result["rollback_artifact_sha256"] == "b" * 64
    with pytest.raises(PermissionError):
        p.require_live_release(db)


def test_evidence_change_invalidates_approvals(db):
    rid = candidate(db)
    populate(db, rid)
    approve(db, rid)
    old = p.snapshot(db, rid)["evidence_digest"]
    p.add_evidence(db, rid, evidence("BANK_UAT"), "INTEGRATION_OWNER")
    status = p.snapshot(db, rid)
    assert old != status["evidence_digest"]
    assert "SIGNOFF: CFO" in status["blockers"]


@pytest.mark.parametrize("failure", ["expiry", "model_version", "disabled_user", "failed_evidence", "rejection"])
def test_live_gate_revalidates_evidence(db, failure):
    rid = candidate(db)
    populate(db, rid)
    approve(db, rid)
    if failure == "expiry":
        db.scalar(select(ProductionEvidence).where(ProductionEvidence.gate == "BANK_UAT")).expires_at = datetime(2000, 1, 1)
    elif failure == "model_version":
        db.scalar(select(ModelRegistryEntry)).version = "2"
    elif failure == "disabled_user":
        db.scalar(select(UserAccount).where(UserAccount.username == "CFO")).active = False
    elif failure == "failed_evidence":
        p.add_evidence(db, rid, evidence("BANK_UAT", result="FAIL"), "INTEGRATION_OWNER")
    else:
        db.scalar(select(ProductionSignoff).where(ProductionSignoff.role == "CFO")).decision = "REJECT"
    db.commit()
    assert p.snapshot(db, rid)["status"] == "BLOCKED"


def test_benchmark_is_deterministic_and_not_certification():
    result = p.benchmark(BenchmarkCreate(actual=[100, 200], predicted=[110, 190], challenger=[120, 220]))
    assert result["mae"] == "10"
    assert result["bias"] == "0"
    assert result["certification"] == "UNVALIDATED"
    with pytest.raises(ValueError):
        p.benchmark(BenchmarkCreate(actual=[1, 2], predicted=[1, 2, 3], challenger=[1, 2]))


@pytest.mark.parametrize("failure", ["synthetic", "missing_metric", "material", "stale", "uat_defect", "restore_target"])
def test_parallel_and_operational_gaps_are_blocking(db, failure):
    rid = candidate(db)
    if failure in {"uat_defect", "restore_target"}:
        request = evidence("BANK_UAT" if failure == "uat_defect" else "RESTORE_FAILOVER")
        request.details["open_material_defects" if failure == "uat_defect" else "rto_seconds"] = 2000
        with pytest.raises(ValueError):
            p.add_evidence(db, rid, request, p.GATES[request.gate])
        return
    populate(db, rid)
    from app.models.production import ProductionObservation
    observations = db.scalars(select(ProductionObservation)).all()
    if failure == "synthetic":
        for record in observations:
            record.kind = "SYNTHETIC"
    elif failure == "missing_metric":
        for record in observations:
            if record.metric == "FX":
                db.delete(record)
    elif failure == "material":
        observations[0].material = True
    else:
        for record in observations:
            if record.day >= (date.today() - timedelta(days=1)).isoformat():
                db.delete(record)
    db.commit()
    assert any("PARALLEL_RUN" in b for b in p.snapshot(db, rid)["blockers"])


def test_api_auth_and_request_limits(db, monkeypatch):
    app.dependency_overrides[get_db] = lambda: db
    try:
        with TestClient(app) as client:
            assert client.get("/health/ready").status_code == 200
            assert client.get("/health/production").status_code == 503
            assert client.get("/api/v1/production/releases/1").status_code == 401
            response = client.post("/api/v1/production/releases", headers={"X-Treasury-User": "maker"},
                json={"name": "api", "artifact_sha256": "a" * 64, "previous_artifact_sha256": "b" * 64})
            assert response.status_code == 200, response.text
            assert client.get(f"/api/v1/production/releases/{response.json()['id']}",
                              headers={"X-Treasury-User": "VIEWER"}).json()["status"] == "BLOCKED"
            monkeypatch.setattr(settings, "max_request_bytes", 10)
            assert client.post("/api/v1/production/releases", content="x" * 11).status_code == 413
            monkeypatch.setattr(settings, "environment", "production")
            assert client.get("/api/v1/liquidity/global", headers={"X-Treasury-User": "maker"}).status_code == 503
    finally:
        app.dependency_overrides.clear()


def test_fresh_cash_cannot_mask_stale_fx_comparisons(db):
    rid = candidate(db)
    populate(db, rid, metric_lag={"FX": 2})
    status = p.snapshot(db, rid)
    assert "PARALLEL_RUN: GROUP/FX observations stale" in status["blockers"]


def test_small_payment_difference_blocks_otherwise_passing_run(db):
    rid = candidate(db)
    populate(db, rid)
    # One mismatch leaves a 98.3% payment pass rate and is below material tolerance.
    p.add_observation(db, rid, ObservationCreate(day=date.today() - timedelta(days=60),
        metric="PAYMENTS", scope="GROUP", kind="REAL", incumbent=100, platform=Decimal("100.01"),
        document_sha256="e" * 64), "TREASURY_ANALYST")
    assert "PARALLEL_RUN: GROUP/PAYMENTS contains unmatched payments" in p.snapshot(db, rid)["blockers"]


def test_halted_release_can_roll_back_without_reenabling_execution(db, monkeypatch):
    rid = candidate(db)
    populate(db, rid)
    approve(db, rid)
    p.transition(db, rid, TransitionCreate(action="START_PARALLEL", reason="test"), "maker")
    p.transition(db, rid, TransitionCreate(action="GO_LIVE", reason="test"), "GROUP_TREASURER")
    monkeypatch.setattr(settings, "production_release_id", rid)
    p.transition(db, rid, TransitionCreate(action="HALT", reason="incident"), "OPERATIONS_MANAGER")
    with pytest.raises(PermissionError):
        p.require_live_release(db)
    result = p.transition(db, rid, TransitionCreate(action="ROLLBACK", reason="recover"), "OPERATIONS_MANAGER")
    assert result["state"] == "ROLLED_BACK"
    assert result["deployment_performed"] is False
    with pytest.raises(PermissionError):
        p.require_live_release(db)


def test_execution_uses_state_from_locked_gate_snapshot(db, monkeypatch):
    rid = candidate(db)
    row = db.get(ProductionRelease, rid)
    row.state = "LIVE"
    db.commit()
    monkeypatch.setattr(settings, "production_release_id", rid)
    # Simulate HALT completing after the initial release lookup but before the lock.
    monkeypatch.setattr(p, "snapshot", lambda db, release_id: {"state": "HALTED", "status": "READY"})
    with pytest.raises(PermissionError):
        p.require_live_release(db)


def test_locked_release_refreshes_previously_cached_state(db):
    from sqlalchemy import update
    rid = candidate(db)
    cached = p.release(db, rid)
    assert cached.state == "DRAFT"
    with Session(db.bind) as writer:
        writer.execute(update(ProductionRelease).where(ProductionRelease.id == rid).values(state="HALTED"))
        writer.commit()
    assert p.release(db, rid).state == "HALTED"
