from decimal import Decimal
from fastapi.testclient import TestClient

from app.main import app


def test_health():
    with TestClient(app) as client:
        res = client.get("/health")
        assert res.status_code == 200
        assert res.json()["status"] == "ok"


def test_global_liquidity_has_positive_group_headroom():
    with TestClient(app) as client:
        res = client.get("/api/v1/liquidity/global")
        assert res.status_code == 200
        body = res.json()
        assert body["reporting_currency"] == "USD"
        assert Decimal(body["liquidity_headroom"]) > 0
        assert len(body["entities"]) == 6


def test_agents_detect_demo_risks():
    with TestClient(app) as client:
        res = client.get("/api/v1/agents/treasury-summary")
        assert res.status_code == 200
        findings = res.json()["findings"]
        titles = {f["title"] for f in findings}
        assert "Stale bank balances" in titles
        assert "High facility utilization" in titles


def test_13_week_base_forecast_remains_above_buffer():
    with TestClient(app) as client:
        res = client.get("/api/v1/liquidity/forecast?scenario=BASE&weeks=13")
        assert res.status_code == 200
        body = res.json()
        assert len(body["points"]) == 13
        assert body["first_buffer_breach_week"] is None
        assert Decimal(body["maximum_shortfall"]) == 0


def test_severe_stress_exposes_liquidity_vulnerability():
    with TestClient(app) as client:
        res = client.get("/api/v1/liquidity/forecast?scenario=SEVERE&weeks=13")
        assert res.status_code == 200
        body = res.json()
        assert body["first_buffer_breach_week"] is not None
        assert Decimal(body["maximum_shortfall"]) > 0


def test_stress_endpoint_compares_three_scenarios():
    with TestClient(app) as client:
        res = client.get("/api/v1/liquidity/stress?weeks=13")
        assert res.status_code == 200
        body = res.json()
        assert [x["scenario"] for x in body] == ["BASE", "MODERATE", "SEVERE"]


def test_derivative_book_and_maturity_summary():
    with TestClient(app) as client:
        positions = client.get("/api/v1/derivatives")
        assert positions.status_code == 200
        body = positions.json()
        assert len(body) >= 5
        assert any(x["instrument_type"] == "INTEREST_RATE_SWAP" for x in body)

        summary = client.get("/api/v1/risk/derivatives")
        assert summary.status_code == 200
        data = summary.json()
        assert data["open_trade_count"] >= 5
        assert Decimal(data["total_notional_reporting"]) > 0
        assert data["unmapped_trade_count"] >= 1


def test_fx_hedge_coverage_detects_control_exception():
    with TestClient(app) as client:
        res = client.get("/api/v1/risk/hedging")
        assert res.status_code == 200
        body = res.json()
        statuses = {x["status"] for x in body}
        assert "UNMATCHED" in statuses
        assert any(x["currency"] == "USD" for x in body)


def test_interest_rate_risk_quantifies_rate_shock():
    with TestClient(app) as client:
        res = client.get("/api/v1/risk/interest-rates")
        assert res.status_code == 200
        body = res.json()
        assert Decimal(body["total_debt"]) > 0
        assert Decimal(body["floating_rate_debt"]) > 0
        assert Decimal(body["pay_fixed_swap_notional"]) > 0
        assert Decimal(body["annual_cash_impact_100bps"]) > 0


def test_counterparty_risk_has_limits_and_pfe():
    with TestClient(app) as client:
        res = client.get("/api/v1/risk/counterparties")
        assert res.status_code == 200
        body = res.json()
        assert len(body) >= 4
        assert all(Decimal(x["potential_future_exposure"]) >= 0 for x in body)
        assert all(Decimal(x["exposure_limit"]) > 0 for x in body)


def test_agents_surface_derivative_control_issue():
    with TestClient(app) as client:
        res = client.get("/api/v1/agents/treasury-summary")
        assert res.status_code == 200
        titles = {x["title"] for x in res.json()["findings"]}
        assert "Unmapped derivative position" in titles


def test_multi_agent_runtime_registers_specialists_and_astra_boundary():
    with TestClient(app) as client:
        res = client.get("/api/v1/agents/runtime")
        assert res.status_code == 200
        body = res.json()
        assert body["model"] == "gpt-6-astra"
        assert len(body["specialist_agents"]) >= 12
        assert "Model Risk Challenger" in body["specialist_agents"]
        assert "Market Stress Engine" in body["deterministic_engines"]


def test_market_stress_quantifies_fx_rate_and_derivative_liquidity_overlay():
    with TestClient(app) as client:
        res = client.get("/api/v1/risk/market-stress?fx_shock_pct=0.10&rate_shock_bps=200")
        assert res.status_code == 200
        body = res.json()
        assert Decimal(body["estimated_fx_adverse_change"]) >= 0
        assert Decimal(body["annual_rate_cash_impact"]) > 0
        assert Decimal(body["combined_market_liquidity_call"]) > 0
        assert len(body["fx_rows"]) >= 1


def test_model_risk_challenger_surfaces_unmapped_hedge():
    with TestClient(app) as client:
        res = client.get("/api/v1/agents/treasury-summary")
        assert res.status_code == 200
        titles = {x["title"] for x in res.json()["findings"]}
        assert "Hedge attribution challenge" in titles


def test_copilot_is_safe_when_llm_credentials_are_not_configured():
    with TestClient(app) as client:
        res = client.post("/api/v1/agents/copilot", json={"question": "What is our main liquidity risk?"})
        assert res.status_code == 200
        body = res.json()
        assert body["model"] == "gpt-6-astra"
        assert body["llm_enabled"] is False
        assert body["answer"] is None
        assert body["deterministic_summary"]["findings"]
        assert "OPENAI_API_KEY" in body["error"]


def test_derivative_mtm_updates_are_audited():
    with TestClient(app) as client:
        positions = client.get("/api/v1/derivatives").json()
        trade_id = positions[0]["id"]
        res = client.post("/api/v1/derivatives/mtm", json={
            "actor": "TEST_MARKET_DATA",
            "updates": [{
                "trade_id": trade_id,
                "market_value_reporting_ccy": "123456.78",
                "source": "TEST_FEED",
            }],
        })
        assert res.status_code == 200
        body = res.json()
        assert trade_id in body["updated_trade_ids"]
        assert body["audit_event_id"] > 0


def test_selective_multi_agent_mode_routes_material_risks_without_live_llm():
    with TestClient(app) as client:
        res = client.post("/api/v1/agents/analyze", json={
            "question": "What should treasury review first?",
            "mode": "SELECTIVE",
        })
        assert res.status_code == 200
        body = res.json()
        assert body["mode"] == "SELECTIVE"
        assert "Model Risk Challenger" in body["selected_agents"]
        assert len(body["insights"]) == len(body["selected_agents"])
        assert all(x["enabled"] is False for x in body["insights"])


def test_cash_mobility_quantifies_trapped_cash_and_multi_currency_accounts():
    with TestClient(app) as client:
        res = client.get("/api/v1/liquidity/mobility")
        assert res.status_code == 200
        body = res.json()
        assert Decimal(body["total_trapped_cash"]) > 0
        assert Decimal(body["total_transferable_surplus"]) > 0
        assert any(x["entity_name"] == "GlobalTech India" and Decimal(x["extra_restrictions_reporting"]) > 0 for x in body["entities"])


def test_cash_pool_identifies_internal_offset_capacity():
    with TestClient(app) as client:
        res = client.get("/api/v1/liquidity/cash-pools")
        assert res.status_code == 200
        body = res.json()
        assert len(body) >= 1
        assert Decimal(body[0]["internal_offset_capacity"]) > 0
        assert any(Decimal(x["funding_need"]) > 0 for x in body[0]["members"])


def test_cross_border_funding_keeps_tax_and_transfer_pricing_review_visible():
    with TestClient(app) as client:
        res = client.get("/api/v1/funding/intercompany")
        assert res.status_code == 200
        body = res.json()
        assert len(body) >= 2
        assert any(x["tax_rule_status"] == "REVIEW_REQUIRED" for x in body)
        assert any(x["transfer_pricing_status"] == "OUTSIDE_CONFIGURED_RANGE" for x in body)


def test_collateral_engine_quantifies_current_and_stressed_margin_calls():
    with TestClient(app) as client:
        res = client.get("/api/v1/risk/collateral")
        assert res.status_code == 200
        body = res.json()
        assert Decimal(body["current_margin_call"]) > 0
        assert Decimal(body["stressed_margin_call"]) > Decimal(body["current_margin_call"])
        assert any(x["status"] == "MARGIN_CALL" for x in body["rows"])


def test_refinancing_engine_detects_facility_expiry_and_covenant_warning():
    with TestClient(app) as client:
        res = client.get("/api/v1/risk/refinancing")
        assert res.status_code == 200
        body = res.json()
        assert Decimal(body["committed_facilities_due_90d"]) > 0
        assert any(x["status"] == "WARNING" for x in body["covenants"])


def test_mvp4_specialist_agents_registered_and_surface_controls():
    with TestClient(app) as client:
        runtime = client.get("/api/v1/agents/runtime").json()
        assert len(runtime["specialist_agents"]) >= 17
        assert "Cash Mobility & Pooling Agent" in runtime["specialist_agents"]
        assert "Collateral & CSA Agent" in runtime["specialist_agents"]

        summary = client.get("/api/v1/agents/treasury-summary").json()
        titles = {x["title"] for x in summary["findings"]}
        assert "Trapped cash identified" in titles
        assert "Covenant headroom narrowing" in titles
        assert "Current collateral liquidity call" in titles


def test_mvp5_rbac_market_data_and_connector_controls_are_exposed():
    with TestClient(app) as client:
        users = client.get("/api/v1/controls/users")
        assert users.status_code == 200
        roles = {x["role"] for x in users.json()}
        assert "TREASURY_ANALYST" in roles
        assert "PAYMENT_OPERATOR" in roles

        feeds = client.get("/api/v1/controls/market-data").json()
        assert any(x["source_type"] == "PRIMARY" and x["execution_usable"] for x in feeds)
        assert any(x["source_type"] == "SECONDARY" and x["stale"] for x in feeds)

        connectors = client.get("/api/v1/controls/connectors").json()
        assert any(x["connector_type"] == "BANK" and x["execution_usable"] for x in connectors)
        assert any(x["connector_type"] == "ERP" and x["execution_usable"] for x in connectors)


def test_mvp5_hedge_accounting_keeps_economic_and_accounting_controls_separate():
    with TestClient(app) as client:
        res = client.get("/api/v1/accounting/hedges")
        assert res.status_code == 200
        body = res.json()
        assert any(x["control_status"] == "READY" for x in body)
        assert any(x["control_status"] == "DOCUMENTATION_GAP" for x in body)


def test_reverse_stress_finds_collection_haircut_threshold():
    with TestClient(app) as client:
        res = client.get("/api/v1/risk/reverse-stress")
        assert res.status_code == 200
        body = res.json()
        assert body["trigger"] == "COLLECTION_HAIRCUT_THRESHOLD"
        haircut = Decimal(body["collection_haircut_pct"])
        assert Decimal("0") < haircut < Decimal("100")
        assert body["first_buffer_breach_week"] is not None


def test_maker_checker_blocks_self_approval():
    with TestClient(app) as client:
        entities = {x["name"]: x["id"] for x in client.get("/api/v1/entities").json()}
        created = client.post("/api/v1/transactions/proposals", headers={"X-Treasury-User": "manager1"}, json={
            "proposal_type": "CASH_TRANSFER",
            "source_entity_id": entities["GlobalTech USA"],
            "target_entity_id": entities["GlobalTech Germany"],
            "currency": "USD",
            "amount": "1000000",
            "purpose": "Test maker-checker segregation",
        })
        assert created.status_code == 200
        proposal_id = created.json()["id"]
        approve = client.post(f"/api/v1/transactions/proposals/{proposal_id}/approve", headers={"X-Treasury-User": "manager1"}, json={
            "decision": "APPROVE",
            "comment": "self approval should fail",
        })
        assert approve.status_code == 403
        assert "Maker-checker" in approve.json()["detail"]


def test_material_transaction_requires_two_levels_and_independent_release():
    with TestClient(app) as client:
        entities = {x["name"]: x["id"] for x in client.get("/api/v1/entities").json()}
        created = client.post("/api/v1/transactions/proposals", headers={"X-Treasury-User": "analyst1"}, json={
            "proposal_type": "FACILITY_DRAW",
            "source_entity_id": entities["GlobalTech USA"],
            "counterparty": "JPMorgan",
            "currency": "USD",
            "amount": "30000000",
            "purpose": "Contingency liquidity draw",
        })
        assert created.status_code == 200
        body = created.json()
        assert body["required_approvals"] == 2
        assert body["status"] == "PENDING_APPROVAL"
        proposal_id = body["id"]

        level1 = client.post(f"/api/v1/transactions/proposals/{proposal_id}/approve", headers={"X-Treasury-User": "manager1"}, json={
            "decision": "APPROVE", "comment": "L1 liquidity review",
        })
        assert level1.status_code == 200
        assert level1.json()["status"] == "PARTIALLY_APPROVED"

        level2 = client.post(f"/api/v1/transactions/proposals/{proposal_id}/approve", headers={"X-Treasury-User": "treasurer1"}, json={
            "decision": "APPROVE", "comment": "Group Treasurer approval",
        })
        assert level2.status_code == 200
        assert level2.json()["status"] == "APPROVED"

        wrong_release = client.post(f"/api/v1/transactions/proposals/{proposal_id}/release", headers={"X-Treasury-User": "treasurer1"}, json={})
        assert wrong_release.status_code == 403

        release = client.post(f"/api/v1/transactions/proposals/{proposal_id}/release", headers={"X-Treasury-User": "executor1"}, json={})
        assert release.status_code == 200
        assert release.json()["status"] == "RELEASED_FOR_EXECUTION"
        assert release.json()["executed_at"] is not None


def test_mvp5_specialist_agents_registered_and_surface_control_findings():
    with TestClient(app) as client:
        runtime = client.get("/api/v1/agents/runtime").json()
        assert len(runtime["specialist_agents"]) >= 21
        assert "Market Data Integrity Agent" in runtime["specialist_agents"]
        assert "Treasury Execution Control Agent" in runtime["specialist_agents"]
        assert "Reverse Stress Search Engine" in runtime["deterministic_engines"]

        summary = client.get("/api/v1/agents/treasury-summary").json()
        titles = {x["title"] for x in summary["findings"]}
        assert "Backup market feed stale" in titles
        assert "Reconciliation exceptions" in titles
        assert "Hedge accounting documentation gap" in titles


def test_stale_primary_fx_feed_blocks_hedge_pretrade():
    from datetime import UTC, datetime, timedelta
    from sqlalchemy import select
    from app.core.db import SessionLocal
    from app.models import MarketDataFeed

    with TestClient(app) as client:
        with SessionLocal() as db:
            feed = db.scalar(select(MarketDataFeed).where(MarketDataFeed.feed_name == "PRIMARY_FX_STREAM"))
            original = feed.last_received_at
            feed.last_received_at = datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=2)
            db.commit()
        try:
            res = client.post("/api/v1/transactions/proposals", headers={"X-Treasury-User": "analyst1"}, json={
                "proposal_type": "FX_HEDGE",
                "currency": "USD",
                "amount": "100000",
                "purpose": "Hedge forecast USD receivable",
                "underlying_reference": "AR-USD-PORTFOLIO",
                })
            assert res.status_code == 200
            body = res.json()
            assert body["status"] == "CONTROL_FAILED"
            assert any(x["code"] == "MARKET_DATA_FRESHNESS" and x["status"] == "BLOCK" for x in body["checks"])
        finally:
            with SessionLocal() as db:
                feed = db.scalar(select(MarketDataFeed).where(MarketDataFeed.feed_name == "PRIMARY_FX_STREAM"))
                feed.last_received_at = original
                db.commit()


def test_failed_reconciliation_blocks_release_even_after_prior_approval():
    from sqlalchemy import select
    from app.core.db import SessionLocal
    from app.models import ReconciliationRun

    with TestClient(app) as client:
        entities = {x["name"]: x["id"] for x in client.get("/api/v1/entities").json()}
        created = client.post("/api/v1/transactions/proposals", headers={"X-Treasury-User": "analyst1"}, json={
            "proposal_type": "CASH_TRANSFER",
            "source_entity_id": entities["GlobalTech USA"],
            "target_entity_id": entities["GlobalTech Germany"],
            "currency": "USD",
            "amount": "500000",
            "purpose": "Test release-time reconciliation gate",
        })
        proposal_id = created.json()["id"]
        approved = client.post(f"/api/v1/transactions/proposals/{proposal_id}/approve", headers={"X-Treasury-User": "manager1"}, json={
            "decision": "APPROVE", "comment": "Approved before recon failure",
        })
        assert approved.json()["status"] == "APPROVED"

        with SessionLocal() as db:
            run = db.scalar(select(ReconciliationRun).where(ReconciliationRun.run_type == "BANK_TO_LEDGER"))
            original_status = run.status
            original_difference = run.difference
            run.status = "FAIL"
            run.difference = Decimal("100000")
            db.commit()
        try:
            released = client.post(f"/api/v1/transactions/proposals/{proposal_id}/release", headers={"X-Treasury-User": "executor1"}, json={})
            assert released.status_code == 409
            assert "controls" in released.json()["detail"].lower()
        finally:
            with SessionLocal() as db:
                run = db.scalar(select(ReconciliationRun).where(ReconciliationRun.run_type == "BANK_TO_LEDGER"))
                run.status = original_status
                run.difference = original_difference
                db.commit()


def test_mvp6_payment_behaviour_ml_validation_and_predictions():
    with TestClient(app) as client:
        validation = client.get("/api/v1/intelligence/model-validation")
        assert validation.status_code == 200
        body = validation.json()
        assert body["validation_status"] in {"PASS", "WATCH"}
        assert body["training_rows"] >= 100
        assert Decimal(body["mae_delay_days"]) >= 0

        preds = client.get("/api/v1/intelligence/payment-predictions").json()
        assert len(preds) >= 10
        assert all(Decimal(x["p90_delay_days"]) >= Decimal(x["p10_delay_days"]) for x in preds)
        assert all(Decimal("0") <= Decimal(x["late_probability"]) <= Decimal("1") for x in preds)


def test_mvp6_model_drift_and_registry_are_governed():
    with TestClient(app) as client:
        drift = client.get("/api/v1/intelligence/model-drift").json()
        assert drift["status"] in {"STABLE", "WATCH", "HIGH"}
        assert Decimal(drift["delay_psi"]) >= 0
        registry = client.get("/api/v1/intelligence/model-registry").json()
        assert any(x["model_code"] == "PAYMENT_BEHAVIOUR_RF" for x in registry)
        assert all(x["data_fingerprint"] for x in registry)


def test_mvp6_ml_cash_forecast_carries_uncertainty_bands():
    with TestClient(app) as client:
        body = client.get("/api/v1/intelligence/cash-forecast?weeks=13").json()
        assert body["model_code"] == "PAYMENT_BEHAVIOUR_RF"
        assert len(body["points"]) == 13
        assert len(body["payment_predictions"]) >= 10
        assert {"expected_headroom", "conservative_headroom", "optimistic_headroom"}.issubset(body["points"][0])


def test_mvp6_intraday_liquidity_prioritisation_and_anomaly_controls():
    with TestClient(app) as client:
        body = client.get("/api/v1/liquidity/intraday").json()
        assert body["first_buffer_breach_bucket"] == "15:00-18:00"
        assert Decimal(body["peak_intraday_funding_need"]) > 0
        discretionary = next(x for x in body["payment_priorities"] if x["payment_reference"] == "TODAY-005")
        assert discretionary["recommended_action"] == "HOLD_FOR_LIQUIDITY_REVIEW"
        anomalies = client.get("/api/v1/risk/payment-anomalies").json()
        assert any(x["payment_reference"] == "TODAY-004" for x in anomalies)


def test_mvp6_independent_price_verification_escalates_material_difference():
    with TestClient(app) as client:
        body = client.get("/api/v1/controls/ipv").json()
        assert body["fail_count"] >= 1
        assert any(x["status"] == "FAIL" for x in body["rows"])
        assert all(x["independent_source_count"] >= 0 for x in body["rows"])


def test_mvp6_market_data_fallback_selects_fresh_secondary_when_primary_stale():
    from datetime import UTC, datetime, timedelta
    from sqlalchemy import select
    from app.core.db import SessionLocal
    from app.models import MarketDataFeed

    with TestClient(app) as client:
        with SessionLocal() as db:
            primary = db.scalar(select(MarketDataFeed).where(MarketDataFeed.feed_name == "PRIMARY_FX_STREAM"))
            secondary = db.scalar(select(MarketDataFeed).where(MarketDataFeed.feed_name == "SECONDARY_FX_BACKUP"))
            op, os = primary.last_received_at, secondary.last_received_at
            primary.last_received_at = datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=2)
            secondary.last_received_at = datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=1)
            db.commit()
        try:
            body = client.get("/api/v1/controls/market-data/fallback?asset_class=FX").json()
            assert body["execution_usable"] is True
            assert body["fallback_used"] is True
            assert body["source_type"] == "SECONDARY"
        finally:
            with SessionLocal() as db:
                primary = db.scalar(select(MarketDataFeed).where(MarketDataFeed.feed_name == "PRIMARY_FX_STREAM"))
                secondary = db.scalar(select(MarketDataFeed).where(MarketDataFeed.feed_name == "SECONDARY_FX_BACKUP"))
                primary.last_received_at, secondary.last_received_at = op, os
                db.commit()


def test_mvp6_screening_potential_match_blocks_pretrade():
    with TestClient(app) as client:
        entities = {x["name"]: x["id"] for x in client.get("/api/v1/entities").json()}
        created = client.post("/api/v1/transactions/proposals", headers={"X-Treasury-User": "analyst1"}, json={
            "proposal_type": "CASH_TRANSFER",
            "source_entity_id": entities["GlobalTech USA"],
            "target_entity_id": entities["GlobalTech Germany"],
            "counterparty": "Rare Counterparty XYZ",
            "currency": "USD",
            "amount": "100000",
            "purpose": "Control test for unresolved screening case",
        })
        assert created.status_code == 200
        body = created.json()
        assert body["status"] == "CONTROL_FAILED"
        assert any(x["code"] == "PAYMENT_SCREENING" and x["status"] == "BLOCK" for x in body["checks"])


def test_mvp6_integrated_scenario_keeps_fx_value_sensitivity_separate_from_cash_overlay():
    with TestClient(app) as client:
        body = client.post("/api/v1/risk/integrated-scenario", json={
            "label": "Combined risk test", "weeks": 13, "receivable_multiplier": "0.65",
            "payable_multiplier": "1.20", "facility_availability": "0.40", "fx_shock_pct": "0.15",
            "rate_shock_bps": 300, "collateral_stress_multiplier": "1.25", "refinancing_spread_shock_bps": 250,
        }).json()
        assert body["status"] in {"RESILIENT", "WATCH", "BREACH"}
        assert Decimal(body["fx_economic_value_sensitivity"]) > 0
        assert any("not automatically treated as a cash outflow" in x for x in body["component_notes"])


def test_mvp6_agent_runtime_has_predictive_and_model_control_agents():
    with TestClient(app) as client:
        runtime = client.get("/api/v1/agents/runtime").json()
        assert len(runtime["specialist_agents"]) >= 29
        assert "ML Cash Forecast Agent" in runtime["specialist_agents"]
        assert "Model Governance & Drift Agent" in runtime["specialist_agents"]
        assert "Independent Price Verification Agent" in runtime["specialist_agents"]
        summary = client.get("/api/v1/agents/treasury-summary").json()
        titles = {x["title"] for x in summary["findings"]}
        assert "Derivative IPV control" in titles
        assert "Model validation and drift status" in titles


def test_mvp7_curve_based_derivative_valuation_prices_full_demo_book():
    with TestClient(app) as client:
        body = client.get("/api/v1/valuation/institutional").json()
        assert body["priced_trade_count"] >= 5
        assert body["unpriced_trade_count"] == 0
        models = {x["model_type"] for x in body["rows"]}
        assert {"FX_FORWARD", "GARMAN_KOHLHAGEN", "IRS_PAR_RATE"}.issubset(models)
        assert all(x["source_quality"] in {"PRIMARY_FRESH", "REVIEW_SOURCE"} for x in body["rows"])


def test_mvp7_liquidity_at_risk_is_seeded_reproducible_and_has_tail_risk():
    with TestClient(app) as client:
        a = client.get("/api/v1/risk/liquidity-at-risk?simulations=1000&seed=77").json()
        b = client.get("/api/v1/risk/liquidity-at-risk?simulations=1000&seed=77").json()
        assert a["p05_ending_headroom"] == b["p05_ending_headroom"]
        assert Decimal(a["cash_flow_at_risk"]) > 0
        assert Decimal(a["liquidity_at_risk"]) >= 0
        assert Decimal("0") <= Decimal(a["probability_of_buffer_breach"]) <= Decimal("1")


def test_mvp7_legal_netting_requires_approved_enforceability():
    with TestClient(app) as client:
        body = client.get("/api/v1/risk/legal-netting").json()
        assert body["legally_enforceable_sets"] >= 1
        assert body["review_required_sets"] >= 1
        dbs = next(x for x in body["rows"] if x["counterparty"] == "DBS")
        assert dbs["status"] == "REVIEW_REQUIRED"
        assert Decimal(dbs["netting_benefit"]) == 0


def test_mvp7_collateral_optimizer_finds_same_currency_capacity_without_auto_movement():
    with TestClient(app) as client:
        body = client.get("/api/v1/risk/collateral-optimization").json()
        assert Decimal(body["total_additional_collateral_required"]) > 0
        row = body["rows"][0]
        assert row["recommended_source_entity"] is not None
        assert row["status"] in {"SAME_CURRENCY_CAPACITY", "CROSS_CURRENCY_FUNDING_REQUIRED"}


def test_mvp7_champion_challenger_never_auto_promotes():
    with TestClient(app) as client:
        body = client.get("/api/v1/intelligence/champion-challenger").json()
        assert body["auto_promotion_allowed"] is False
        assert body["recommendation"] in {"KEEP_CHAMPION", "INDEPENDENT_VALIDATION_FOR_PROMOTION", "INSUFFICIENT_DATA"}
        assert Decimal(body["promotion_threshold_pct"]) > 0


def test_mvp7_operational_resilience_surfaces_tier1_gap():
    with TestClient(app) as client:
        body = client.get("/api/v1/ops/resilience").json()
        assert body["tier1_count"] >= 3
        assert body["tier1_gaps"] >= 1
        assert any(x["component_name"] == "Payment Release Service" and x["status"] == "GAP" for x in body["components"])


def test_mvp7_observability_and_security_headers_are_active():
    with TestClient(app) as client:
        health = client.get("/health")
        assert health.status_code == 200
        assert health.json()["version"] == "0.10.0"
        assert health.headers.get("x-request-id")
        assert health.headers.get("x-content-type-options") == "nosniff"
        ready = client.get("/health/ready")
        assert ready.status_code == 200
        metrics = client.get("/metrics")
        assert metrics.status_code == 200
        assert "treasury_http_requests_total" in metrics.text


def test_mvp7_runtime_registers_institutional_agents_and_engines():
    with TestClient(app) as client:
        runtime = client.get("/api/v1/agents/runtime").json()
        assert len(runtime["specialist_agents"]) >= 35
        assert "Institutional Pricing & Valuation Agent" in runtime["specialist_agents"]
        assert "Liquidity-at-Risk Agent" in runtime["specialist_agents"]
        assert "Operational Resilience & Security Agent" in runtime["specialist_agents"]
        assert "Curve-Based Derivative Pricing Engine" in runtime["deterministic_engines"]
        assert "Legal Netting Set Engine" in runtime["deterministic_engines"]


def test_mvp7_security_posture_exposes_production_boundaries_without_claiming_demo_auth_is_sso():
    with TestClient(app) as client:
        body = client.get("/api/v1/ops/security").json()
        assert body["demo_identity_blocked_in_production"] is True
        assert body["write_idempotency_required_in_production"] is True
        assert body["security_headers_enabled"] is True


def test_mvp7_connector_circuit_breaker_opens_after_repeated_failure():
    import asyncio
    from app.integrations.resilient import ConnectorCircuitBreaker, ResilientConnectorRunner, RetryPolicy, CircuitState, CircuitOpenError

    breaker = ConnectorCircuitBreaker(failure_threshold=2, recovery_seconds=60)
    runner = ResilientConnectorRunner(breaker, RetryPolicy(max_attempts=1, base_delay_seconds=0))

    async def fail():
        raise RuntimeError("synthetic connector failure")

    for _ in range(2):
        try:
            asyncio.run(runner.call(fail))
        except RuntimeError:
            pass
    assert breaker.state == CircuitState.OPEN
    try:
        asyncio.run(runner.call(fail))
        assert False, "open circuit should reject the connector call"
    except CircuitOpenError:
        pass



def test_mvp8_event_ingestion_is_idempotent_and_detects_key_collision():
    from datetime import UTC, datetime
    from sqlalchemy import select
    from app.core.db import SessionLocal
    from app.models import BankAccount

    with TestClient(app) as client:
        with SessionLocal() as db:
            account = db.scalar(select(BankAccount).where(BankAccount.bank_name == "JPMorgan"))
            account_id = account.id
            book = str(account.book_balance)
            restricted = str(account.restricted_balance)
            committed = str(account.committed_outflows)
        payload = {
            "source_system": "MULTI_BANK_API",
            "connector_name": "GLOBAL_BANK_API",
            "event_type": "BANK_BALANCE",
            "idempotency_key": "TEST-MVP8-BANK-IDEMPOTENT-1",
            "event_time": datetime.now(UTC).isoformat(),
            "sequence_no": 1002,
            "payload": {
                "account_id": account_id,
                "book_balance": book,
                "restricted_balance": restricted,
                "committed_outflows": committed,
            },
        }
        first = client.post("/api/v1/events/ingest", headers={"X-Connector-Name": "GLOBAL_BANK_API"}, json=payload)
        assert first.status_code == 200
        assert first.json()["duplicate"] is False
        assert first.json()["event"]["processing_status"] == "APPLIED"

        duplicate = client.post("/api/v1/events/ingest", headers={"X-Connector-Name": "GLOBAL_BANK_API"}, json=payload)
        assert duplicate.status_code == 200
        assert duplicate.json()["duplicate"] is True
        assert duplicate.json()["event"]["id"] == first.json()["event"]["id"]

        collision = dict(payload)
        collision["payload"] = dict(payload["payload"])
        collision["payload"]["book_balance"] = str(Decimal(book) + Decimal("1"))
        collided = client.post("/api/v1/events/ingest", headers={"X-Connector-Name": "GLOBAL_BANK_API"}, json=collision)
        assert collided.status_code == 409
        assert "collision" in collided.json()["detail"].lower()


def test_mvp8_out_of_order_sequence_is_quarantined_not_projected():
    from datetime import UTC, datetime
    with TestClient(app) as client:
        body = {
            "source_system": "MULTI_BANK_API",
            "connector_name": "GLOBAL_BANK_API",
            "event_type": "CONNECTOR_HEARTBEAT",
            "idempotency_key": "TEST-MVP8-OLD-SEQUENCE",
            "event_time": datetime.now(UTC).isoformat(),
            "sequence_no": 1001,
            "payload": {"status": "ACTIVE"},
        }
        res = client.post("/api/v1/events/ingest", headers={"X-Connector-Name": "GLOBAL_BANK_API"}, json=body)
        assert res.status_code == 200
        assert res.json()["projected"] is False
        assert res.json()["event"]["processing_status"] == "QUARANTINED_SEQUENCE"


def test_mvp8_erp_event_projects_into_current_cashflow_state():
    from datetime import UTC, datetime, date, timedelta
    from sqlalchemy import select
    from app.core.db import SessionLocal
    from app.models import CashFlow, LegalEntity

    with TestClient(app) as client:
        with SessionLocal() as db:
            us = db.scalar(select(LegalEntity).where(LegalEntity.country_code == "US"))
        ref = "TEST-MVP8-ERP-CF-001"
        body = {
            "source_system": "SAP_S4",
            "connector_name": "GLOBAL_ERP",
            "event_type": "ERP_CASH_FLOW",
            "idempotency_key": "TEST-MVP8-ERP-EVENT-001",
            "external_reference": ref,
            "entity_id": us.id,
            "event_time": datetime.now(UTC).isoformat(),
            "sequence_no": 2202,
            "payload": {
                "source_reference": ref,
                "entity_id": us.id,
                "flow_type": "RECEIVABLE",
                "counterparty": "Live ERP Test Customer",
                "currency": "USD",
                "amount": "1000",
                "due_date": (date.today() + timedelta(days=14)).isoformat(),
                "probability": "0.90",
                "status": "OPEN",
            },
        }
        res = client.post("/api/v1/events/ingest", headers={"X-Connector-Name": "GLOBAL_ERP"}, json=body)
        assert res.status_code == 200
        assert res.json()["projected"] is True
        with SessionLocal() as db:
            row = db.scalar(select(CashFlow).where(CashFlow.source_reference == ref))
            assert row is not None
            assert Decimal(row.amount) == Decimal("1000")
            assert row.counterparty == "Live ERP Test Customer"


def test_mvp8_live_monitor_creates_alerts_but_never_transactions():
    with TestClient(app) as client:
        before = len(client.get("/api/v1/transactions/proposals").json())
        res = client.post("/api/v1/operations/monitor/run", headers={"X-Treasury-User": "risk1"})
        assert res.status_code == 200
        body = res.json()
        assert body["status"] in {"NORMAL", "WATCH", "CRITICAL"}
        assert Decimal(body["lar_buffer_breach_probability"]) >= 0
        assert any("cannot" in x.lower() and "transaction" in x.lower() for x in body["notes"])
        after = len(client.get("/api/v1/transactions/proposals").json())
        assert before == after
        alerts = client.get("/api/v1/operations/alerts").json()
        assert any(x["category"] in {"LIQUIDITY_AT_RISK", "INTRADAY_LIQUIDITY"} for x in alerts)


def test_mvp8_live_alert_acknowledgement_is_audited_human_action():
    with TestClient(app) as client:
        client.post("/api/v1/operations/monitor/run", headers={"X-Treasury-User": "risk1"})
        alerts = client.get("/api/v1/operations/alerts?status=OPEN").json()
        assert alerts
        target = alerts[0]
        ack = client.post(f"/api/v1/operations/alerts/{target['id']}/ack", headers={"X-Treasury-User": "risk1"}, json={"comment": "Reviewed by risk"})
        assert ack.status_code == 200
        assert ack.json()["status"] == "ACKNOWLEDGED"
        assert ack.json()["acknowledged_by"] == "risk1"


def test_mvp8_execution_message_requires_release_then_bank_acknowledgement():
    with TestClient(app) as client:
        entities = {x["name"]: x["id"] for x in client.get("/api/v1/entities").json()}
        created = client.post("/api/v1/transactions/proposals", headers={"X-Treasury-User": "analyst1"}, json={
            "proposal_type": "CASH_TRANSFER",
            "source_entity_id": entities["GlobalTech USA"],
            "target_entity_id": entities["GlobalTech Germany"],
            "currency": "USD",
            "amount": "100000",
            "purpose": "MVP8 execution acknowledgement control test",
        })
        assert created.status_code == 200
        proposal_id = created.json()["id"]
        approved = client.post(f"/api/v1/transactions/proposals/{proposal_id}/approve", headers={"X-Treasury-User": "manager1"}, json={"decision": "APPROVE", "comment": "approved"})
        assert approved.status_code == 200
        released = client.post(f"/api/v1/transactions/proposals/{proposal_id}/release", headers={"X-Treasury-User": "executor1"}, json={})
        assert released.status_code == 200
        assert released.json()["status"] == "RELEASED_FOR_EXECUTION"

        msg = client.post(
            f"/api/v1/transactions/proposals/{proposal_id}/execution-message",
            headers={"X-Treasury-User": "executor1", "Idempotency-Key": "MVP8-EXEC-MSG-001"},
            json={"connector_name": "GLOBAL_BANK_API", "idempotency_key": "MVP8-EXEC-MSG-001"},
        )
        assert msg.status_code == 200
        m = msg.json()
        assert m["status"] == "QUEUED"
        assert m["signature"]

        sent = client.post(f"/api/v1/execution/messages/{m['message_id']}/sent", headers={"X-Connector-Name": "GLOBAL_BANK_API"})
        assert sent.status_code == 200
        assert sent.json()["status"] == "SENT"

        ack = client.post(f"/api/v1/execution/messages/{m['message_id']}/ack", headers={"X-Connector-Name": "GLOBAL_BANK_API"}, json={
            "status": "ACKNOWLEDGED", "external_reference": "BANK-ACK-12345", "detail": "Accepted by synthetic bank connector",
        })
        assert ack.status_code == 200
        assert ack.json()["status"] == "ACKNOWLEDGED"
        assert ack.json()["external_reference"] == "BANK-ACK-12345"


def test_mvp8_execution_message_idempotency_does_not_duplicate_instruction():
    with TestClient(app) as client:
        rows = client.get("/api/v1/execution/messages").json()
        if not rows:
            entities = {x["name"]: x["id"] for x in client.get("/api/v1/entities").json()}
            created = client.post("/api/v1/transactions/proposals", headers={"X-Treasury-User": "analyst1"}, json={
                "proposal_type": "CASH_TRANSFER", "source_entity_id": entities["GlobalTech USA"],
                "target_entity_id": entities["GlobalTech Germany"], "currency": "USD", "amount": "100000",
                "purpose": "Self-contained idempotency test",
            })
            proposal_id = created.json()["id"]
            client.post(f"/api/v1/transactions/proposals/{proposal_id}/approve", headers={"X-Treasury-User": "manager1"}, json={"decision": "APPROVE", "comment": "approved"})
            client.post(f"/api/v1/transactions/proposals/{proposal_id}/release", headers={"X-Treasury-User": "executor1"}, json={})
            client.post(
                f"/api/v1/transactions/proposals/{proposal_id}/execution-message",
                headers={"X-Treasury-User": "executor1", "Idempotency-Key": "MVP8-SELF-CONTAINED"},
                json={"connector_name": "GLOBAL_BANK_API", "idempotency_key": "MVP8-SELF-CONTAINED"},
            )
            rows = client.get("/api/v1/execution/messages").json()
        assert rows
        existing = rows[0]
        replay = client.post(
            f"/api/v1/transactions/proposals/{existing['proposal_id']}/execution-message",
            headers={"X-Treasury-User": "executor1", "Idempotency-Key": existing["idempotency_key"]},
            json={"connector_name": existing["connector_name"], "idempotency_key": existing["idempotency_key"]},
        )
        assert replay.status_code == 200
        assert replay.json()["message_id"] == existing["message_id"]


def test_mvp8_runtime_registers_live_operations_agents_and_engines():
    with TestClient(app) as client:
        runtime = client.get("/api/v1/agents/runtime").json()
        assert len(runtime["specialist_agents"]) >= 39
        assert "Live Event Integrity Agent" in runtime["specialist_agents"]
        assert "Continuous Treasury Monitoring Agent" in runtime["specialist_agents"]
        assert "Immutable Treasury Event Ledger & Projection Engine" in runtime["deterministic_engines"]
        assert "External bank acknowledgement required for completion" in runtime["controls"]
        status = client.get("/api/v1/operations/live-status").json()
        assert status["events_24h"] >= 3
        assert len(status["checkpoints"]) >= 3


def test_mvp9_hedge_optimizer_respects_policy_and_does_not_add_unmatched_risk():
    with TestClient(app) as client:
        body = client.post("/api/v1/optimization/hedges", json={"target_hedge_ratio": "0.75", "option_share": "0.25"}).json()
        assert body["reporting_currency"] == "USD"
        assert Decimal(body["total_incremental_hedge_reporting"]) >= 0
        unmatched = next(x for x in body["rows"] if x["currency"] == "JPY")
        assert unmatched["action"] == "UNWIND_REVIEW"
        assert Decimal(unmatched["forward_notional"]) == 0
        for row in body["rows"]:
            if row["status"] in {"FEASIBLE", "POLICY_CONSTRAINED"}:
                target = Decimal(row["target_hedge_ratio"])
                assert Decimal(row["policy_min"]) <= target <= Decimal(row["policy_max"])


def test_mvp9_funding_optimizer_avoids_double_counting_intercompany_capacity():
    with TestClient(app) as client:
        body = client.get("/api/v1/optimization/funding").json()
        assert Decimal(body["requested_funding_need"]) > 0
        assert Decimal(body["covered_funding"]) <= Decimal(body["requested_funding_need"])
        assert len(body["intercompany_structuring_options"]) >= 1
        source_types = {x["source_type"] for x in body["rows"]}
        assert "INTERCOMPANY_FACILITY" not in source_types
        assert any("double counting" in x.lower() for x in body["warnings"])


def test_mvp9_cash_pool_optimizer_produces_non_executable_sweeps_only():
    with TestClient(app) as client:
        body = client.get("/api/v1/optimization/cash-pool").json()
        assert Decimal(body["total_internal_offset"]) > 0
        assert body["instruction_count"] >= 1
        assert all(x["status"] == "PROPOSED_NOT_EXECUTABLE" for x in body["instructions"])


def test_mvp9_scenario_search_finds_multi_factor_breaches_without_probabilities():
    with TestClient(app) as client:
        body = client.get("/api/v1/optimization/scenario-search?top_n=5").json()
        assert body["combinations_tested"] == 324
        assert body["breach_count"] > 0
        assert Decimal(body["worst_stressed_headroom"]) < 0
        assert body["rows"][0]["rank"] == 1
        assert "not a probability" in body["warnings"][0].lower()


def test_mvp9_decision_pack_has_three_governed_strategies_and_no_execution_authority():
    with TestClient(app) as client:
        body = client.get("/api/v1/optimization/decision-pack?objective=BALANCED").json()
        assert body["recommended_strategy_code"] == "BALANCED"
        assert {x["strategy_code"] for x in body["strategies"]} == {"LIQUIDITY_PRESERVATION", "BALANCED", "RISK_REDUCTION"}
        assert body["human_approval_required"] is True
        assert body["execution_authority"] == "NONE"
        assert all(Decimal(x["resilience_score"]) >= 0 for x in body["strategies"])


def test_mvp9_runtime_registers_optimization_committee_agents_and_engines():
    with TestClient(app) as client:
        runtime = client.get("/api/v1/agents/runtime").json()
        assert len(runtime["specialist_agents"]) >= 45
        assert "Portfolio Hedge Optimization Agent" in runtime["specialist_agents"]
        assert "Treasury Decision Committee Agent" in runtime["specialist_agents"]
        assert "Multi-Factor Treasury Scenario Search Engine" in runtime["deterministic_engines"]
        assert "No AI or optimizer execution authority" in runtime["controls"]


def test_mvp9_health_version():
    with TestClient(app) as client:
        assert client.get("/health").json()["version"] == "0.10.0"

# MVP-10 digital twin and enterprise risk intelligence
def test_market_var_and_ear_are_seeded_and_non_negative():
    with TestClient(app) as client:
        a = client.get("/api/v1/risk/market-var?horizon_days=10&simulations=2000&seed=42")
        b = client.get("/api/v1/risk/market-var?horizon_days=10&simulations=2000&seed=42")
        assert a.status_code == 200
        assert b.status_code == 200
        body = a.json()
        assert Decimal(body["portfolio_var_95"]) >= 0
        assert Decimal(body["portfolio_expected_shortfall_95"]) >= Decimal(body["portfolio_var_95"])
        assert Decimal(body["earnings_at_risk_95_90d"]) >= 0
        assert body["portfolio_var_95"] == b.json()["portfolio_var_95"]


def test_liquidity_transfer_pricing_is_management_pricing():
    with TestClient(app) as client:
        res = client.get("/api/v1/liquidity/transfer-pricing")
        assert res.status_code == 200
        body = res.json()
        assert Decimal(body["deficit_charge_rate"]) > Decimal(body["surplus_credit_rate"])
        assert len(body["rows"]) == 6
        assert all(x["status"] == "MANAGEMENT_PRICING_ONLY" for x in body["rows"])


def test_bank_account_rationalization_preserves_pool_infrastructure():
    with TestClient(app) as client:
        res = client.get("/api/v1/operations/bank-account-rationalization")
        assert res.status_code == 200
        body = res.json()
        assert body["account_count"] >= 6
        pool_rows = [x for x in body["rows"] if x["role"] == "POOL_INFRASTRUCTURE"]
        assert pool_rows
        assert all(x["recommendation"] == "RETAIN" for x in pool_rows)


def test_digital_twin_preserves_execution_boundary_and_risk_layers():
    with TestClient(app) as client:
        res = client.get("/api/v1/digital-twin")
        assert res.status_code == 200
        body = res.json()
        assert body["twin_version"] == "MVP-10.0"
        assert body["state"] in {"RESILIENT", "WATCH", "STRESSED"}
        assert Decimal(body["liquidity_at_risk_95"]) >= 0
        assert Decimal(body["market_var_95"]) >= 0
        assert body["scenario"]["reporting_currency"] == body["reporting_currency"]
        assert any("decision-support" in x.lower() for x in body["assumptions"])


def test_digital_twin_custom_scenario_can_be_stressed():
    with TestClient(app) as client:
        res = client.post("/api/v1/digital-twin/simulate", json={
            "label": "Severe twin",
            "weeks": 13,
            "receivable_multiplier": "0.45",
            "payable_multiplier": "1.25",
            "facility_availability": "0.35",
            "fx_shock_pct": "0.15",
            "rate_shock_bps": 300,
            "collateral_stress_multiplier": "1.50",
            "refinancing_spread_shock_bps": 250
        })
        assert res.status_code == 200
        body = res.json()
        assert body["state"] == "STRESSED"
        assert Decimal(body["scenario_stressed_headroom"]) < 0


def test_mvp10_specialist_agents_are_registered():
    with TestClient(app) as client:
        res = client.get("/api/v1/agents/runtime")
        assert res.status_code == 200
        body = res.json()
        assert len(body["specialist_agents"]) >= 50
        assert "Treasury Digital Twin Agent" in body["specialist_agents"]
        assert "Market VaR & EaR Agent" in body["specialist_agents"]
        assert "Treasury Digital Twin Engine" in body["deterministic_engines"]

# MVP-11 institutional counterparty, funding concentration and survival-risk layer
def test_mvp11_historical_calibration_uses_dynamic_correlations():
    with TestClient(app) as client:
        res = client.get("/api/v1/risk/historical-calibration?lookback_observations=120&ewma_lambda=0.94")
        assert res.status_code == 200
        body = res.json()
        assert body["lookback_observations"] >= 100
        assert len(body["factors"]) >= 4
        assert len(body["correlations"]) >= 3
        assert any(abs(Decimal(x["correlation"])) > Decimal("0.10") for x in body["correlations"])


def test_mvp11_historical_market_var_replaces_static_correlation_as_primary_twin_view():
    with TestClient(app) as client:
        hist = client.get("/api/v1/risk/historical-market-var")
        twin = client.get("/api/v1/digital-twin")
        assert hist.status_code == 200
        assert twin.status_code == 200
        h = hist.json(); t = twin.json()
        assert h["correlation_method"].startswith("EWMA_")
        assert Decimal(h["portfolio_var"]) > 0
        assert Decimal(t["market_var_95"]) == Decimal(h["portfolio_var"])
        assert t["institutional_depth_version"] == "MVP-11.0"


def test_mvp11_xva_is_sensitivity_not_accounting_claim():
    with TestClient(app) as client:
        res = client.get("/api/v1/risk/xva")
        assert res.status_code == 200
        body = res.json()
        assert Decimal(body["total_xva_style_adjustment"]) >= 0
        assert body["rows"]
        assert any("not accounting fair-value" in x.lower() for x in body["warnings"])


def test_mvp11_survival_horizon_and_funding_concentration_are_quantified():
    with TestClient(app) as client:
        survival = client.get("/api/v1/liquidity/survival-horizon")
        concentration = client.get("/api/v1/funding/concentration")
        assert survival.status_code == 200
        assert concentration.status_code == 200
        s = survival.json(); f = concentration.json()
        assert s["survival_horizon_days"] >= 0
        assert s["status"] in {"SURVIVES_HORIZON", "BREACH", "CRITICAL"}
        assert Decimal(f["top_lender_share"]) > 0
        assert Decimal(f["hhi"]) > 0
        assert f["lender_count"] >= 4


def test_mvp11_treasury_limit_framework_is_deterministic_and_governed():
    with TestClient(app) as client:
        res = client.get("/api/v1/risk/limits")
        assert res.status_code == 200
        body = res.json()
        assert body["overall_status"] in {"WITHIN_LIMITS", "WARNING", "BREACH"}
        assert len(body["rows"]) >= 5
        assert {x["metric_name"] for x in body["rows"]} >= {"SURVIVAL_HORIZON_DAYS", "TOP_LENDER_SHARE", "FX_VAR_95_10D"}


def test_mvp11_digital_twin_optimizer_has_no_execution_authority():
    with TestClient(app) as client:
        res = client.post("/api/v1/digital-twin/optimize", json={"objective": "LIQUIDITY_RESILIENCE", "weeks": 13})
        assert res.status_code == 200
        body = res.json()
        assert body["combinations_tested"] == 54
        assert body["execution_authority"] == "NONE"
        assert body["scenarios"]
        assert body["scenarios"][0]["rank"] == 1


def test_mvp11_runtime_registers_institutional_depth_agents_and_engines():
    with TestClient(app) as client:
        res = client.get("/api/v1/agents/runtime")
        assert res.status_code == 200
        body = res.json()
        assert len(body["specialist_agents"]) >= 56
        for name in [
            "Historical Market Calibration Agent",
            "Counterparty XVA Sensitivity Agent",
            "Liquidity Survival Horizon Agent",
            "Funding Concentration Agent",
            "Treasury Risk Limit Framework Agent",
            "Digital Twin Scenario Optimizer Agent",
        ]:
            assert name in body["specialist_agents"]
        assert "Historical EWMA Volatility & Dynamic Correlation Engine" in body["deterministic_engines"]


def test_mvp12_structural_liquidity_gap_has_maturity_ladder_and_keeps_facilities_separate():
    with TestClient(app) as client:
        res = client.get("/api/v1/liquidity/structural-gap")
        assert res.status_code == 200
        body = res.json()
        assert len(body["rows"]) == 7
        assert Decimal(body["opening_deployable_cash"]) > 0
        assert any(Decimal(x["debt_maturities"]) > 0 for x in body["rows"])
        assert "facilities" in " ".join(body["warnings"]).lower()


def test_mvp12_rate_gap_dv01_separates_cash_and_value_sensitivity():
    with TestClient(app) as client:
        res = client.get("/api/v1/risk/rate-gap-dv01")
        assert res.status_code == 200
        body = res.json()
        assert Decimal(body["residual_floating_reporting"]) > 0
        assert Decimal(body["annual_cash_impact_100bps"]) > 0
        assert Decimal(body["combined_dv01_proxy_reporting"]) != 0
        assert any("proxy" in x.lower() for x in body["warnings"])


def test_mvp12_funding_tenor_optimizer_is_advisory_and_fully_allocates_target():
    with TestClient(app) as client:
        res = client.get("/api/v1/optimization/funding-tenor")
        assert res.status_code == 200
        body = res.json()
        assert body["execution_authority"] == "NONE"
        assert sum(Decimal(x["target_share"]) for x in body["rows"]) == Decimal("1.00")
        assert sum(Decimal(x["proposed_amount_reporting"]) for x in body["rows"]).quantize(Decimal("0.01")) == Decimal(body["requested_new_funding"]).quantize(Decimal("0.01"))


def test_mvp12_contingency_plan_does_not_double_count_liquidity_sources():
    with TestClient(app) as client:
        res = client.get("/api/v1/liquidity/contingency-funding-plan")
        assert res.status_code == 200
        body = res.json()
        used = sum(Decimal(x["modeled_use_reporting"]) for x in body["actions"])
        need = Decimal(body["reference_tail_funding_need"])
        assert used <= need
        assert body["execution_authority"] == "NONE"


def test_mvp12_early_warning_framework_has_directional_thresholds():
    with TestClient(app) as client:
        res = client.get("/api/v1/risk/early-warning")
        assert res.status_code == 200
        body = res.json()
        assert body["overall_status"] in {"GREEN", "AMBER", "RED"}
        assert {x["direction"] for x in body["indicators"]}.issubset({"MAX", "MIN"})
        assert any(x["indicator_code"] == "SURVIVAL_HORIZON_DAYS" for x in body["indicators"])


def test_mvp12_balance_sheet_twin_can_generate_critical_stress_without_execution_authority():
    with TestClient(app) as client:
        res = client.post("/api/v1/digital-twin/balance-sheet/simulate", json={
            "label": "MVP12 severe",
            "weeks": 26,
            "receivable_multiplier": "0.40",
            "payable_multiplier": "1.30",
            "facility_availability": "0.25",
            "fx_shock_pct": "0.20",
            "rate_shock_bps": 400,
            "collateral_stress_multiplier": "1.50",
            "refinancing_spread_shock_bps": 300,
        })
        assert res.status_code == 200
        body = res.json()
        assert body["status"] == "CRITICAL"
        assert Decimal(body["stressed_liquidity_headroom"]) < 0
        assert body["execution_authority"] == "NONE"


def test_mvp12_runtime_registers_liquidity_command_agents_and_engines():
    with TestClient(app) as client:
        res = client.get("/api/v1/agents/runtime")
        assert res.status_code == 200
        body = res.json()
        assert len(body["specialist_agents"]) >= 63
        assert "Structural Liquidity Gap Agent" in body["specialist_agents"]
        assert "Predictive Balance-Sheet Twin Agent" in body["specialist_agents"]
        assert "Structural Liquidity Maturity Ladder Engine" in body["deterministic_engines"]
        assert "Predictive Balance-Sheet Treasury Twin Engine" in body["deterministic_engines"]

# MVP-13 deep liquidity-risk intelligence
def test_mvp13_liquidity_concentration_preserves_transferability_boundary():
    with TestClient(app) as client:
        res = client.get("/api/v1/liquidity/concentration")
        assert res.status_code == 200
        body = res.json()
        assert len(body["rows"]) == 3
        assert {x["dimension"] for x in body["rows"]} == {"LEGAL_ENTITY", "BANK", "CURRENCY"}
        assert Decimal(body["deployable_cash"]) > 0
        assert Decimal(body["trapped_cash_share"]) >= 0
        assert Decimal(body["transferability_ratio"]) >= 0
        assert any("transferability" in x.lower() for x in body["warnings"])


def test_mvp13_probabilistic_liquidity_path_is_seeded_and_path_based():
    with TestClient(app) as client:
        a = client.get("/api/v1/liquidity/probabilistic-path?horizon_weeks=13&simulations=1000&seed=77")
        b = client.get("/api/v1/liquidity/probabilistic-path?horizon_weeks=13&simulations=1000&seed=77")
        assert a.status_code == 200 and b.status_code == 200
        body = a.json()
        assert body["probability_of_any_buffer_breach"] == b.json()["probability_of_any_buffer_breach"]
        assert len(body["weekly_distribution"]) == 13
        assert Decimal(body["tail_funding_need_95"]) >= 0
        assert Decimal(body["p05_minimum_headroom"]) <= Decimal(body["p95_minimum_headroom"])


def test_mvp13_stress_attribution_preserves_fx_cash_transmission_boundary():
    with TestClient(app) as client:
        res = client.post("/api/v1/liquidity/stress-attribution", json={
            "label": "MVP13 attribution",
            "weeks": 13,
            "receivable_multiplier": "0.65",
            "payable_multiplier": "1.20",
            "facility_availability": "0.50",
            "fx_shock_pct": "0.15",
            "rate_shock_bps": 250,
            "collateral_stress_multiplier": "1.25",
            "refinancing_spread_shock_bps": 200
        })
        assert res.status_code == 200
        body = res.json()
        drivers = {x["driver"]: x for x in body["rows"]}
        assert {"COLLECTIONS", "PAYABLES", "FACILITY_AVAILABILITY", "FX", "RATES", "COLLATERAL", "REFINANCING"}.issubset(drivers)
        assert "Economic value" in drivers["FX"]["liquidity_transmission"]
        assert Decimal(body["total_deterioration"]) > 0


def test_mvp13_forecast_driver_concentration_is_probability_weighted():
    with TestClient(app) as client:
        res = client.get("/api/v1/liquidity/forecast-drivers?horizon_weeks=13&top_n=10")
        assert res.status_code == 200
        body = res.json()
        assert Decimal(body["absolute_projected_flow_base"]) > 0
        assert body["rows"]
        assert Decimal(body["top_five_driver_share"]) <= Decimal("1.000001")
        assert any("probability-weighted" in x.lower() for x in body["warnings"])


def test_mvp13_liquidity_action_playbook_has_no_execution_authority():
    with TestClient(app) as client:
        res = client.get("/api/v1/liquidity/action-playbook")
        assert res.status_code == 200
        body = res.json()
        assert body["actions"]
        assert all(x["execution_authority"] == "NONE" for x in body["actions"])
        assert Decimal(body["quantified_capacity_total"]) >= 0
        assert Decimal(body["residual_uncovered_need"]) >= 0
        assert any("not independently added" in x.lower() for x in body["warnings"])


def test_mvp13_runtime_registers_deep_liquidity_intelligence():
    with TestClient(app) as client:
        res = client.get("/api/v1/agents/runtime")
        assert res.status_code == 200
        body = res.json()
        assert len(body["specialist_agents"]) >= 68
        for name in [
            "Liquidity Concentration Agent",
            "Probabilistic Liquidity Path Agent",
            "Liquidity Stress Attribution Agent",
            "Forecast Driver Concentration Agent",
            "Liquidity Action Playbook Agent",
        ]:
            assert name in body["specialist_agents"]
        assert "Probabilistic Weekly Liquidity Path Engine" in body["deterministic_engines"]
        assert "Liquidity Stress Attribution Engine" in body["deterministic_engines"]


def test_mvp13_liquidity_question_routes_on_demand_specialists_without_execution_authority():
    with TestClient(app) as client:
        res = client.post("/api/v1/agents/analyze", json={
            "question": "Analyze liquidity risk, cash buffers, funding and forecast vulnerabilities",
            "mode": "SELECTIVE",
        })
        assert res.status_code == 200
        body = res.json()
        assert "Liquidity Stress Attribution Agent" in body["selected_agents"]
        assert "Liquidity Concentration Agent" in body["selected_agents"]
        assert body["insights"]  # safe-off Astra responses are still recorded as specialist attempts
        assert all(x["enabled"] is False for x in body["insights"])

# MVP-14 forecast accuracy and working-capital liquidity intelligence
def test_mvp14_forecast_accuracy_uses_realized_history_and_flags_bias():
    with TestClient(app) as client:
        res = client.get("/api/v1/liquidity/forecast-accuracy?lookback_days=180")
        assert res.status_code == 200
        body = res.json()
        assert body["observation_count"] >= 90
        assert Decimal(body["overall_wape"]) > 0
        assert Decimal(body["cash_bias_pct"]) > 0
        assert body["status"] in {"PASS", "WATCH", "FAIL"}
        assert {x["segment_type"] for x in body["rows"]} == {"FLOW_TYPE", "HORIZON"}
        assert any("WAPE" in x for x in body["warnings"])


def test_mvp14_forecast_bias_direction_is_liquidity_consistent():
    with TestClient(app) as client:
        res = client.get("/api/v1/liquidity/forecast-bias")
        assert res.status_code == 200
        body = res.json()
        assert body["optimistic_bias_entities"] >= 1
        assert body["rows"]
        assert all(Decimal(x["cash_bias_pct"]) > 0 for x in body["rows"])
        assert all(Decimal(x["outflow_bias_pct"]) < 0 for x in body["rows"])


def test_mvp14_working_capital_cycle_has_true_dso_dpo_dio_ccc():
    with TestClient(app) as client:
        res = client.get("/api/v1/working-capital/cycle")
        assert res.status_code == 200
        body = res.json()
        assert Decimal(body["group_dso_days"]) > 0
        assert Decimal(body["group_dpo_days"]) > 0
        assert Decimal(body["group_dio_days"]) > 0
        assert Decimal(body["group_ccc_days"]) == (
            Decimal(body["group_dso_days"]) + Decimal(body["group_dio_days"]) - Decimal(body["group_dpo_days"])
        ).quantize(Decimal("0.01"))
        assert len(body["rows"]) >= 3


def test_mvp14_receivables_aging_separates_collection_probability_from_accounting_loss():
    with TestClient(app) as client:
        res = client.get("/api/v1/working-capital/receivables-aging")
        assert res.status_code == 200
        body = res.json()
        assert Decimal(body["total_open_receivables"]) > Decimal(body["total_overdue_receivables"]) > 0
        assert {x["bucket"] for x in body["buckets"]} == {"CURRENT", "1-30", "31-60", "61-90", "90+"}
        assert body["top_overdue_counterparties"]
        assert any("not a credit-loss" in x.lower() for x in body["warnings"])


def test_mvp14_working_capital_bridge_is_advisory_and_reconciles_components():
    with TestClient(app) as client:
        res = client.post("/api/v1/working-capital/liquidity-bridge", json={
            "dso_improvement_days": "5",
            "dpo_extension_days": "3",
            "dio_improvement_days": "4",
        })
        assert res.status_code == 200
        body = res.json()
        total = Decimal(body["dso_cash_release"]) + Decimal(body["dpo_cash_release"]) + Decimal(body["inventory_cash_release"])
        assert total.quantize(Decimal("0.01")) == Decimal(body["total_modeled_cash_release"]).quantize(Decimal("0.01"))
        assert Decimal(body["pro_forma_liquidity_headroom"]) > Decimal(body["current_liquidity_headroom"])
        assert body["execution_authority"] == "NONE"


def test_mvp14_runtime_registers_forecast_and_working_capital_specialists():
    with TestClient(app) as client:
        res = client.get("/api/v1/agents/runtime")
        assert res.status_code == 200
        body = res.json()
        assert len(body["specialist_agents"]) >= 72
        for name in [
            "Forecast Accuracy & Bias Agent",
            "Working Capital Cycle Agent",
            "Receivables Collection Risk Agent",
            "Working Capital Liquidity Agent",
        ]:
            assert name in body["specialist_agents"]
        assert "Forecast Accuracy & Bias Engine" in body["deterministic_engines"]
        assert "Working Capital Cycle Engine" in body["deterministic_engines"]


def test_mvp14_working_capital_question_routes_specialists_without_execution_authority():
    with TestClient(app) as client:
        res = client.post("/api/v1/agents/analyze", json={
            "question": "Analyze working capital, DSO, receivables and cash forecast accuracy",
            "mode": "SELECTIVE",
        })
        assert res.status_code == 200
        body = res.json()
        assert "Forecast Accuracy & Bias Agent" in body["selected_agents"]
        assert "Working Capital Cycle Agent" in body["selected_agents"]
        assert "Receivables Collection Risk Agent" in body["selected_agents"]
        # AI is safe-off in tests; deterministic specialists are still routed and audited.
        assert all(x["enabled"] is False for x in body["insights"])


def test_mvp15_cross_border_constraint_graph_and_projected_liquidity_routing():
    with TestClient(app) as client:
        graph = client.get("/api/v1/global-treasury/cross-border-constraints")
        assert graph.status_code == 200
        body = graph.json()
        assert body["executable_route_count"] >= 1
        assert body["blocked_route_count"] >= 1

        opt = client.get("/api/v1/optimization/legal-entity-liquidity")
        assert opt.status_code == 200
        data = opt.json()
        assert Decimal(data["local_deficit"]) > 0
        assert Decimal(data["proposed_transfer"]) > 0
        assert Decimal(data["unresolved_deficit"]) >= 0
        assert data["execution_authority"] == "NONE"
        assert any(x["status"] == "PROPOSED" for x in data["routes"])
        assert any(x["status"] == "BLOCKED" for x in data["routes"])


def test_mvp16_connector_readiness_exposes_degraded_and_blocked_integrations():
    with TestClient(app) as client:
        res = client.get("/api/v1/integrations/readiness")
        assert res.status_code == 200
        body = res.json()
        assert body["ready_count"] >= 1
        assert body["blocked_count"] >= 1
        assert body["canonical_contract_version"] == "MVP16-1.0"
        assert any(x["connector_type"] == "MARKET" and x["readiness"] == "BLOCKED" for x in body["rows"])


def test_mvp17_security_posture_does_not_claim_production_readiness_without_evidence():
    with TestClient(app) as client:
        res = client.get("/api/v1/security/enterprise-posture")
        assert res.status_code == 200
        body = res.json()
        assert body["overall_status"] == "BLOCKED"
        assert body["failing_controls"] >= 1
        assert any(x["control_code"] == "PEN_TEST" and x["status"] != "PASS" for x in body["rows"])


def test_mvp18_model_validation_dashboard_preserves_independent_validation_gate():
    with TestClient(app) as client:
        res = client.get("/api/v1/models/validation-dashboard")
        assert res.status_code == 200
        body = res.json()
        assert body["validation_count"] >= 3
        assert body["pass_count"] >= 2
        assert body["watch_count"] >= 1
        assert any(x["validation_type"] == "BENCHMARK" for x in body["rows"])


def test_mvp19_role_workspaces_are_role_specific():
    with TestClient(app) as client:
        cfo = client.get("/api/v1/workspaces/CFO")
        risk = client.get("/api/v1/workspaces/RISK")
        ops = client.get("/api/v1/workspaces/TREASURY_OPERATIONS")
        assert cfo.status_code == risk.status_code == ops.status_code == 200
        assert cfo.json()["open_items"] >= risk.json()["open_items"]
        assert all(x["owner_role"] == "RISK" for x in risk.json()["queue"])
        assert "Reconciliations" in ops.json()["recommended_panels"]


def test_mvp20_production_gate_is_honest_no_go_in_synthetic_environment():
    with TestClient(app) as client:
        res = client.get("/api/v1/production/readiness")
        assert res.status_code == 200
        body = res.json()
        assert body["release"] == "MVP-22"
        assert body["overall_status"] == "NO_GO"
        assert body["blocked_controls"] > 0
        assert body["deployment_authority"] == "HUMAN_RELEASE_BOARD_ONLY"


def test_five_top_level_astra_agent_teams_preserve_specialist_coverage():
    with TestClient(app) as client:
        res = client.get("/api/v1/agents/runtime")
        assert res.status_code == 200
        body = res.json()
        assert len(body["top_level_agents"]) == 5
        assert set(body["top_level_agents"]) == {
            "Liquidity & Funding Agent",
            "Market & Derivatives Risk Agent",
            "Global Treasury & Tax Agent",
            "Risk, Controls & Model Governance Agent",
            "Treasury Orchestrator & Decision Agent",
        }
        assert len(body["specialist_agents"]) >= 72

# MVP-21 / MVP-22 predictive risk and strategic treasury
def test_mvp21_treasury_risk_radar_is_governed_and_non_executable():
    with TestClient(app) as client:
        res = client.get('/api/v1/intelligence/treasury-risk-radar?horizon_days=90')
        assert res.status_code == 200
        body = res.json()
        assert body['overall_status'] in {'GREEN', 'AMBER', 'RED'}
        assert Decimal(body['deterioration_score']) >= 0
        assert Decimal(body['deterioration_score']) <= 1
        assert len(body['dynamic_scenarios']) == 3
        assert body['execution_authority'] == 'NONE'
        assert any('not a calibrated probability' in w for w in body['warnings'])


def test_mvp21_radar_rejects_invalid_horizon():
    with TestClient(app) as client:
        res = client.get('/api/v1/intelligence/treasury-risk-radar?horizon_days=10')
        assert res.status_code == 422


def test_mvp22_liquidity_buffer_has_ordered_bounds():
    with TestClient(app) as client:
        res = client.get('/api/v1/strategy/optimal-liquidity-buffer')
        assert res.status_code == 200
        body = res.json()
        lower = Decimal(body['lower_buffer_bound'])
        recommended = Decimal(body['recommended_buffer'])
        upper = Decimal(body['upper_buffer_bound'])
        assert lower <= recommended <= upper
        assert body['execution_authority'] == 'NONE'
        assert len(body['components']) >= 4


def test_mvp22_strategic_plan_compares_three_non_executable_options():
    with TestClient(app) as client:
        res = client.post('/api/v1/strategy/treasury-plan', json={
            'horizon_years': 3,
            'objective': 'BALANCED',
        })
        assert res.status_code == 200
        body = res.json()
        assert body['selected_strategy_code'] == 'BALANCED'
        assert len(body['strategies']) == 3
        assert body['human_approval_required'] is True
        assert body['execution_authority'] == 'NONE'
        assert all(x['cost_data_completeness'] == 'INCOMPLETE_EXECUTABLE_PRICING' for x in body['strategies'])


def test_mvp22_strategic_plan_rejects_invalid_horizon():
    with TestClient(app) as client:
        res = client.post('/api/v1/strategy/treasury-plan', json={'horizon_years': 10, 'objective': 'BALANCED'})
        assert res.status_code == 400


def test_runtime_exposes_mvp21_22_engines_and_five_top_level_agents():
    with TestClient(app) as client:
        res = client.get('/api/v1/agents/runtime')
        assert res.status_code == 200
        body = res.json()
        assert len(body['top_level_agents']) == 5
        engines = set(body['deterministic_engines'])
        assert 'Predictive Treasury Risk Radar Engine' in engines
        assert 'Multi-Year Treasury Strategy Optimization Engine' in engines
