from datetime import date, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient

from app.main import app


def _headers(connector: str | None = None):
    h = {"X-Treasury-User": "integration.owner"}
    if connector:
        h["X-Connector-Name"] = connector
    return h


def test_default_authority_is_shadow_and_bank_balance_is_staged():
    with TestClient(app) as client:
        auth = client.get("/api/v1/integrations/phase1/authority")
        assert auth.status_code == 200, auth.text
        row = next(x for x in auth.json() if x["connector_code"] == "SWIFT_ISO20022" and x["data_domain"] == "BANK_BALANCE")
        assert row["mode"] == "SHADOW"

        resp = client.post("/api/v1/integrations/phase1/bank/balances", headers=_headers("SWIFT_ISO20022"), json={
            "connector_code": "SWIFT_ISO20022",
            "source_system": "SWIFT_UAT",
            "schema_version": "1.0",
            "balances": [{
                "external_account_id": "DEMO-US-001",
                "currency": "USD",
                "book_balance": "47000000",
                "available_balance": "46500000",
                "as_of": "2026-10-03T11:00:00Z",
                "source_record_id": "SHADOW-BAL-001"
            }]
        })
        assert resp.status_code == 200, resp.text
        assert resp.json()["applied"] == 1
        assert any("SHADOW mode" in x for x in resp.json()["warnings"])
        shadow = client.get("/api/v1/integrations/phase1/shadow-records?connector_code=SWIFT_ISO20022&data_domain=BANK_BALANCE")
        assert shadow.status_code == 200
        assert any(x["source_record_id"] == "SHADOW-BAL-001" for x in shadow.json())


def test_active_promotion_is_blocked_without_full_certification():
    with TestClient(app) as client:
        resp = client.patch(
            "/api/v1/integrations/phase1/authority/SWIFT_ISO20022/BANK_BALANCE",
            headers=_headers(),
            json={"mode": "ACTIVE", "evidence": "attempted early promotion"},
        )
        assert resp.status_code == 400
        assert "certification" in resp.json()["detail"].lower()


def test_parallel_run_summary_becomes_ready_with_sustained_passes():
    with TestClient(app) as client:
        for i in range(10):
            d = date.today() - timedelta(days=i)
            resp = client.post("/api/v1/integrations/phase1/parallel-run/observations", headers=_headers(), json={
                "connector_code": "SWIFT_ISO20022",
                "data_domain": "BANK_BALANCE",
                "observation_date": str(d),
                "metric_name": "GLOBAL_CASH_USD",
                "incumbent_value": "100000000",
                "platform_value": str(Decimal("100000000") + Decimal(i * 10000)),
                "tolerance_pct": "0.005",
                "evidence": f"parallel day {i+1}",
            })
            assert resp.status_code == 200, resp.text
            assert resp.json()["status"] == "PASS"
        summary = client.get("/api/v1/integrations/phase1/parallel-run/summary?connector_code=SWIFT_ISO20022&data_domain=BANK_BALANCE&window_days=30")
        assert summary.status_code == 200, summary.text
        body = summary.json()
        assert body["distinct_observation_days"] >= 10
        assert Decimal(str(body["pass_rate"])) >= Decimal("0.95")
        assert body["status"] == "READY"


def test_data_quality_sla_is_explicit_and_governed():
    with TestClient(app) as client:
        result = client.post(
            "/api/v1/integrations/phase1/data-quality/SWIFT_ISO20022/BANK_BALANCE",
            headers=_headers(),
        )
        assert result.status_code == 200, result.text
        body = result.json()
        assert body["data_domain"] == "BANK_BALANCE"
        assert body["status"] in {"PASS", "WATCH", "FAIL"}
        for key in ["timeliness_score", "completeness_score", "validity_score", "uniqueness_score", "reconciliation_score", "overall_score"]:
            value = Decimal(str(body[key]))
            assert Decimal("0") <= value <= Decimal("1")


def test_quarantine_resolution_has_named_actor_and_evidence():
    with TestClient(app) as client:
        bad = client.post("/api/v1/integrations/phase1/bank/balances", headers=_headers("SWIFT_ISO20022"), json={
            "connector_code": "SWIFT_ISO20022",
            "source_system": "SWIFT_UAT",
            "schema_version": "1.0",
            "balances": [{
                "external_account_id": "NOT-MAPPED-V2",
                "currency": "USD",
                "book_balance": "100",
                "available_balance": "100",
                "as_of": "2026-10-03T11:00:00Z",
                "source_record_id": "QUAR-V2-001"
            }]
        })
        assert bad.status_code == 200
        q = client.get("/api/v1/integrations/phase1/quarantine?open_only=true")
        target = next(x for x in q.json() if x["source_reference"] == "QUAR-V2-001")
        resolved = client.patch(
            f"/api/v1/integrations/phase1/quarantine/{target['id']}/resolve",
            headers=_headers(), json={"resolution": "Mapped record reviewed; source master-data ticket opened."},
        )
        assert resolved.status_code == 200, resolved.text
        assert resolved.json()["resolved"] is True
        assert resolved.json()["resolved_by"] == "integration.owner"


def test_parallel_readiness_does_not_overstate_production_state():
    with TestClient(app) as client:
        status = client.get("/api/v1/integrations/phase1/parallel-readiness")
        assert status.status_code == 200, status.text
        body = status.json()
        assert body["status"] in {"PARALLEL_VALIDATION", "READY_FOR_CONTROLLED_PROMOTION"}
        assert body["shadow_authority_count"] >= 1
        assert isinstance(body["blockers"], list)
