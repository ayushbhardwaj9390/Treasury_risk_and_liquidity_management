"""Fail-closed governance. Synthetic results never qualify as production evidence."""
import hashlib
import json
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import ModelRegistryEntry, UserAccount, SourceAuthorityPolicy, DataQualitySLAResult, LiveTreasuryAlert
from app.models.production import (
    ProductionRelease, ProductionEvidence, ProductionSignoff,
    ProductionObservation, ProductionEvent,
)
from app.services.enterprise_controls import _user
from app.services.production_phase1 import parallel_readiness

# Each external attestation is accountable to a separate enterprise role.
GATES = {
    "BANK_UAT": "INTEGRATION_OWNER", "ERP_UAT": "INTEGRATION_OWNER",
    "MARKET_LICENSE": "INTEGRATION_OWNER", "MODEL_VALIDATION": "RISK_MANAGER",
    "SECURITY_REVIEW": "SECURITY_OFFICER", "PENETRATION_TEST": "SECURITY_OFFICER",
    "IDENTITY_KMS_SIEM": "SECURITY_OFFICER", "RESTORE_FAILOVER": "OPERATIONS_MANAGER",
    "LOAD_TEST": "OPERATIONS_MANAGER", "MONITORING": "OPERATIONS_MANAGER",
    "ROLLBACK_REHEARSAL": "OPERATIONS_MANAGER", "TREASURY_UAT": "GROUP_TREASURER",
    "PAYMENTS_UAT": "PAYMENT_OPERATOR", "ACCOUNTING_UAT": "ACCOUNTING_REVIEWER",
    "TAX_VALIDATION": "TAX_REVIEWER", "LEGAL_VALIDATION": "LEGAL_REVIEWER",
    "AUDIT_REVIEW": "AUDITOR",
}
SIGNOFF_ROLES = set(GATES.values()) | {"CFO"}
METRICS = {"CASH", "FORECAST", "FX", "LIQUIDITY", "PAYMENTS", "RISK"}


def now():
    return datetime.now(UTC).replace(tzinfo=None)


def actor_role(db, actor, roles):
    user = _user(db, actor)
    if user.role not in roles:
        raise PermissionError("Active enterprise role required: " + ", ".join(sorted(roles)))
    return user.role


def release(db, release_id):
    row = db.scalar(select(ProductionRelease).where(ProductionRelease.id == release_id)
                    .with_for_update().execution_options(populate_existing=True))
    if row is None:
        raise LookupError("Release not found")
    return row


def editable(row):
    if row.state not in {"DRAFT", "PARALLEL"}:
        raise ValueError("Release evidence is frozen; create a new release")


def event(db, row, action, actor, reason):
    db.add(ProductionEvent(release_id=row.id, action=action, actor=actor,
                           reason=reason, recorded_at=now()))


def create_release(db, request, actor):
    actor_role(db, actor, {"GROUP_TREASURER"})
    if request.artifact_sha256 == request.previous_artifact_sha256:
        raise ValueError("Rollback target must differ from candidate")
    row = ProductionRelease(**request.model_dump(), created_by=actor, created_at=now())
    db.add(row)
    db.flush()
    event(db, row, "CREATE", actor, "Candidate and rollback artifact hashes registered")
    db.commit()
    return {"id": row.id, "state": row.state}


def add_evidence(db, release_id, request, actor):
    row = release(db, release_id)
    editable(row)
    if request.gate not in GATES:
        raise ValueError("Unknown required gate")
    actor_role(db, actor, {GATES[request.gate]})
    expiry = request.expires_at.astimezone(UTC).replace(tzinfo=None)
    if expiry <= now() or expiry > now() + timedelta(days=90):
        raise ValueError("Evidence expiry must be in the next 90 days")
    if request.gate == "MODEL_VALIDATION":
        d = request.details
        if not d.get("model_version") or not d.get("developer") or d["developer"] == actor:
            raise ValueError("Versioned independent validation requires a different developer")
        if not d.get("benchmark_sha256") or not d.get("limitations"):
            raise ValueError("Benchmark digest and limitations are mandatory")
    if request.gate in {"RESTORE_FAILOVER", "ROLLBACK_REHEARSAL"}:
        d = request.details
        for key in ("rto_seconds", "rpo_seconds"):
            value = d.get(key)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= (1800 if key == "rto_seconds" else 300):
                raise ValueError("Measured RTO <=1800s and RPO <=300s required")
    if request.gate.endswith("_UAT") and request.result == "PASS":
        cases = request.details.get("cases", [])
        if not cases or not isinstance(cases, list) or any(
            not isinstance(case, dict) or not all(case.get(key) for key in ("id", "expected", "actual", "document_sha256"))
            or case.get("result") != "PASS" for case in cases
        ) or request.details.get("open_material_defects") != 0:
            raise ValueError("UAT PASS requires passing cases with expected/actual evidence and zero open material defects")
    data = request.model_dump(exclude={"details", "expires_at"})
    evidence = ProductionEvidence(**data, release_id=row.id, recorded_by=actor,
                                  recorded_at=now(), expires_at=expiry,
                                  details_json=json.dumps(request.details, sort_keys=True, allow_nan=False))
    db.add(evidence)
    event(db, row, "EVIDENCE", actor, request.gate)
    db.commit()
    return {"id": evidence.id, "qualifies": request.kind == "REAL" and request.result == "PASS"}


def add_observation(db, release_id, request, actor):
    row = release(db, release_id)
    editable(row)
    actor_role(db, actor, {"TREASURY_ANALYST", "INTEGRATION_OWNER"})
    if request.day > date.today():
        raise ValueError("Future observations are forbidden")
    difference = abs(request.platform - request.incumbent)
    variance = difference / abs(request.incumbent) if request.incumbent else (Decimal(0) if difference == 0 else Decimal("Infinity"))
    # Fixed tolerances cannot be relaxed by API clients. Payments require equality.
    passed = difference == 0 if request.metric == "PAYMENTS" else variance <= Decimal("0.005")
    data = request.model_dump(exclude={"day", "incumbent", "platform"})
    record = ProductionObservation(**data, release_id=row.id, day=request.day.isoformat(),
                                   incumbent=str(request.incumbent), platform=str(request.platform),
                                   passed=passed, material=variance > Decimal("0.02"), actor=actor)
    db.add(record)
    event(db, row, "OBSERVATION", actor, request.metric)
    db.commit()
    return {"id": record.id, "passed": passed, "material": record.material}


def snapshot(db, release_id):
    row = release(db, release_id)
    evidence = db.scalars(select(ProductionEvidence).where(ProductionEvidence.release_id == row.id).order_by(ProductionEvidence.id)).all()
    observations = db.scalars(select(ProductionObservation).where(ProductionObservation.release_id == row.id).order_by(ProductionObservation.id)).all()
    content = {"artifact": row.artifact_sha256, "rollback": row.previous_artifact_sha256,
               "evidence": [(r.id, r.gate, r.kind, r.result, r.document_sha256, r.reference, r.scope,
                             r.recorded_by, r.expires_at.isoformat(), r.details_json) for r in evidence],
               "observations": [(r.id, r.day, r.metric, r.scope, r.kind, r.incumbent, r.platform,
                                 r.document_sha256, r.actor, r.passed, r.material) for r in observations]}
    digest = hashlib.sha256(json.dumps(content, sort_keys=True).encode()).hexdigest()
    latest = {}
    for item in evidence:
        latest[item.gate] = item
    blockers = []
    for gate in GATES:
        item = latest.get(gate)
        if item is None or item.kind != "REAL" or item.result != "PASS" or item.expires_at <= now():
            blockers.append(gate + ": missing, synthetic, failed or expired external evidence")
    validation = latest.get("MODEL_VALIDATION")
    inventory = db.scalars(select(ModelRegistryEntry)).all()
    covered = json.loads(validation.details_json).get("models", {}) if validation else {}
    if not inventory or any(covered.get(m.model_code) != m.version for m in inventory):
        blockers.append("MODEL_VALIDATION: current model inventory/version coverage incomplete")
    recent = [r for r in observations if r.kind == "REAL" and r.day >= (date.today() - timedelta(days=89)).isoformat()]
    if not recent:
        blockers.append("PARALLEL_RUN: no real observations")
    # Enforce 60 observation days per scope and metric; aggregation cannot hide gaps.
    scopes = {r.scope for r in recent}
    for scope in sorted(scopes):
        for metric in sorted(METRICS):
            records = [r for r in recent if r.scope == scope and r.metric == metric]
            if len({r.day for r in records}) < 60 or not records or sum(r.passed for r in records) / len(records) < .95 or any(r.material for r in records):
                blockers.append(f"PARALLEL_RUN: {scope}/{metric} requires 60 days, 95% pass and no material variance")
            if records and max(r.day for r in records) < (date.today() - timedelta(days=1)).isoformat():
                blockers.append(f"PARALLEL_RUN: {scope}/{metric} observations stale")
            if metric == "PAYMENTS" and any(not r.passed for r in records):
                blockers.append(f"PARALLEL_RUN: {scope}/PAYMENTS contains unmatched payments")
    signs = db.scalars(select(ProductionSignoff).where(ProductionSignoff.release_id == row.id, ProductionSignoff.evidence_digest == digest)).all()
    for role in sorted(SIGNOFF_ROLES):
        qualifying = [s for s in signs if s.role == role and s.decision == "APPROVE"
                      and db.scalar(select(UserAccount).where(UserAccount.username == s.actor,
                                    UserAccount.active.is_(True), UserAccount.role == role)) is not None]
        if not qualifying:
            blockers.append("SIGNOFF: " + role)
    if any(s.decision == "REJECT" for s in signs):
        blockers.append("SIGNOFF: human rejection")
    integration = parallel_readiness(db)
    if integration.status != "READY_FOR_CONTROLLED_PROMOTION":
        blockers.append("PHASE1: real-data coverage, reconciliation or source authority incomplete")
    for source in db.scalars(select(SourceAuthorityPolicy).where(SourceAuthorityPolicy.mode == "ACTIVE")):
        quality = db.scalar(select(DataQualitySLAResult).where(
            DataQualitySLAResult.connector_code == source.connector_code,
            DataQualitySLAResult.data_domain == source.data_domain).order_by(DataQualitySLAResult.as_of.desc()).limit(1))
        if quality is None or quality.status != "PASS" or quality.as_of < now() - timedelta(hours=24):
            blockers.append(f"DATA_QUALITY: {source.connector_code}/{source.data_domain} stale or failed")
    if db.scalar(select(LiveTreasuryAlert).where(LiveTreasuryAlert.severity == "CRITICAL", LiveTreasuryAlert.status != "RESOLVED")):
        blockers.append("MONITORING: unresolved critical treasury alert")
    return {"release_id": row.id, "state": row.state, "evidence_digest": digest,
            "status": "READY" if not blockers else "BLOCKED", "blockers": blockers,
            "required_gates": GATES, "required_signoff_roles": sorted(SIGNOFF_ROLES),
            "real_observation_count": len(recent), "autonomous_execution": False,
            "model_inventory": {m.model_code: m.version for m in inventory}}


def signoff(db, release_id, request, actor):
    row = release(db, release_id)
    editable(row)
    role = actor_role(db, actor, SIGNOFF_ROLES)
    if actor == row.created_by:
        raise PermissionError("Release maker cannot sign off their own release")
    current = snapshot(db, row.id)
    if request.evidence_digest != current["evidence_digest"]:
        raise ValueError("Evidence changed; review the current digest")
    if request.decision == "APPROVE" and any(not b.startswith("SIGNOFF:") for b in current["blockers"]):
        raise ValueError("Cannot approve incomplete production evidence")
    db.add(ProductionSignoff(**request.model_dump(), release_id=row.id, role=role, actor=actor, signed_at=now()))
    event(db, row, "SIGNOFF", actor, request.reason)
    db.commit()
    return snapshot(db, row.id)


def transition(db, release_id, request, actor):
    row = release(db, release_id)
    actor_role(db, actor, {"GROUP_TREASURER", "OPERATIONS_MANAGER"} if request.action in {"HALT", "ROLLBACK"} else {"GROUP_TREASURER"})
    if request.action == "START_PARALLEL":
        if row.state != "DRAFT":
            raise ValueError("Only draft releases can start parallel validation")
        target = "PARALLEL"
    elif request.action == "GO_LIVE":
        if row.state != "PARALLEL" or actor == row.created_by:
            raise PermissionError("Independent treasurer must promote a parallel release")
        gate = snapshot(db, row.id)
        if gate["status"] != "READY":
            raise ValueError("Go-live blocked: " + "; ".join(gate["blockers"]))
        if db.scalar(select(ProductionRelease).where(ProductionRelease.state == "LIVE")):
            raise ValueError("Another live release exists")
        target = "LIVE"
    else:
        allowed_states = {"LIVE", "HALTED"} if request.action == "ROLLBACK" else {"LIVE"}
        if row.state not in allowed_states:
            raise ValueError("Rollback requires a live or halted release; halt requires a live release")
        target = "ROLLED_BACK" if request.action == "ROLLBACK" else "HALTED"
    row.state = target
    event(db, row, request.action, actor, request.reason)
    db.commit()
    return {"state": target, "deployment_performed": False,
            "rollback_artifact_sha256": row.previous_artifact_sha256,
            "message": "Governance decision recorded. Deployment/restore requires the approved operator runbook."}


def require_live_release(db):
    if not settings.production_release_id:
        raise PermissionError("Production execution blocked by release governance")
    gate = snapshot(db, settings.production_release_id)
    if gate["state"] != "LIVE" or gate["status"] != "READY":
        raise PermissionError("Production execution blocked by release governance")


def benchmark(request):
    vectors = (request.actual, request.predicted, request.challenger)
    if len({len(v) for v in vectors}) != 1 or any(not x.is_finite() for v in vectors for x in v):
        raise ValueError("Equal-length finite benchmark vectors required")
    n = Decimal(len(request.actual))
    mae = sum(abs(a - p) for a, p in zip(request.actual, request.predicted)) / n
    challenger_mae = sum(abs(a - c) for a, c in zip(request.actual, request.challenger)) / n
    bias = sum(p - a for a, p in zip(request.actual, request.predicted)) / n
    return {"rows": int(n), "mae": str(mae), "bias": str(bias), "challenger_mae": str(challenger_mae),
            "outperforms_challenger": mae < challenger_mae,
            "certification": "UNVALIDATED", "human_independent_validation_required": True}
