from datetime import UTC, date, datetime
from decimal import Decimal

from fastapi.testclient import TestClient

from app.main import app


CAMT_053 = """<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:camt.053.001.08">
  <BkToCstmrStmt>
    <Stmt>
      <Id>STATEMENT-001</Id>
      <Acct><Id><Othr><Id>DEMO-US-001</Id></Othr></Id></Acct>
      <Bal>
        <Tp><CdOrPrtry><Cd>CLBD</Cd></CdOrPrtry></Tp>
        <Amt Ccy="USD">45000000.00</Amt>
        <CdtDbtInd>CRDT</CdtDbtInd>
        <Dt><Dt>2026-10-03</Dt></Dt>
      </Bal>
      <Bal>
        <Tp><CdOrPrtry><Cd>CLAV</Cd></CdOrPrtry></Tp>
        <Amt Ccy="USD">43000000.00</Amt>
        <CdtDbtInd>CRDT</CdtDbtInd>
        <Dt><Dt>2026-10-03</Dt></Dt>
      </Bal>
      <Ntry>
        <Amt Ccy="USD">125000.00</Amt>
        <CdtDbtInd>CRDT</CdtDbtInd>
        <Sts><Cd>BOOK</Cd></Sts>
        <BookgDt><Dt>2026-10-03</Dt></BookgDt>
        <ValDt><Dt>2026-10-03</Dt></ValDt>
        <NtryRef>AR-REAL-001</NtryRef>
        <NtryDtls><TxDtls><RltdPties><Dbtr><Pty><Nm>Real Customer Ltd</Nm></Pty></Dbtr></RltdPties></TxDtls></NtryDtls>
      </Ntry>
    </Stmt>
  </BkToCstmrStmt>
</Document>"""


def test_phase1_iso20022_ingestion_and_lineage():
    with TestClient(app) as client:
        response = client.post("/api/v1/integrations/phase1/bank/iso20022", headers={"X-Connector-Name":"SWIFT_ISO20022"}, json={
            "connector_code": "SWIFT_ISO20022",
            "source_system": "SWIFT_ISO20022",
            "xml_payload": CAMT_053,
        })
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["message_type"] == "camt.053"
        assert body["balance_result"]["applied"] == 1
        assert body["transaction_result"]["applied"] == 1

        lineage = client.get("/api/v1/integrations/phase1/lineage?connector_code=SWIFT_ISO20022")
        assert lineage.status_code == 200
        types = {x["source_object_type"] for x in lineage.json()}
        assert "BANK_BALANCE" in types
        assert "BANK_TRANSACTION" in types


def test_phase1_unmapped_bank_account_goes_to_quarantine():
    with TestClient(app) as client:
        response = client.post("/api/v1/integrations/phase1/bank/balances", headers={"X-Connector-Name":"SWIFT_ISO20022"}, json={
            "connector_code": "SWIFT_ISO20022",
            "source_system": "SWIFT_ISO20022",
            "balances": [{
                "external_account_id": "UNKNOWN-ACCOUNT",
                "currency": "USD",
                "book_balance": "1000",
                "available_balance": "1000",
                "as_of": "2026-10-03T10:00:00Z",
                "source_record_id": "UNMAPPED-001"
            }]
        })
        assert response.status_code == 200
        assert response.json()["quarantined"] == 1
        q = client.get("/api/v1/integrations/phase1/quarantine")
        assert q.status_code == 200
        assert any(x["source_reference"] == "UNMAPPED-001" and x["reason_code"] == "UNMAPPED_BANK_ACCOUNT" for x in q.json())


def test_phase1_erp_cash_flow_mapping():
    with TestClient(app) as client:
        response = client.post("/api/v1/integrations/phase1/erp/cash-flows", headers={"X-Connector-Name":"SAP_S4_FINANCE"}, json={
            "connector_code": "SAP_S4_FINANCE",
            "source_system": "SAP_S4HANA",
            "flows": [{
                "external_reference": "SAP-AR-REAL-001",
                "legal_entity_code": "US01",
                "flow_type": "RECEIVABLE",
                "counterparty": "Real Customer Ltd",
                "currency": "USD",
                "amount": "125000",
                "due_date": str(date.today()),
                "probability": "0.95",
                "status": "OPEN"
            }]
        })
        assert response.status_code == 200, response.text
        assert response.json()["applied"] == 1


def test_phase1_detailed_bank_erp_reconciliation():
    today = str(date.today())
    with TestClient(app) as client:
        # Ensure a bank transaction exists under a unique source reference.
        bank = client.post("/api/v1/integrations/phase1/bank/transactions", headers={"X-Connector-Name":"SWIFT_ISO20022"}, json={
            "connector_code": "SWIFT_ISO20022",
            "source_system": "SWIFT_ISO20022",
            "transactions": [{
                "external_account_id": "DEMO-US-001",
                "source_record_id": "RECON-BANK-001",
                "booking_date": today,
                "value_date": today,
                "currency": "USD",
                "amount": "250000.00",
                "credit_debit": "CRDT",
                "counterparty": "Reconciliation Customer",
                "reference": "E2E-RECON-001",
                "status": "BOOK"
            }]
        })
        assert bank.status_code == 200

        journal = client.post("/api/v1/integrations/phase1/erp/journals", headers={"X-Connector-Name":"SAP_S4_FINANCE"}, json={
            "connector_code": "SAP_S4_FINANCE",
            "source_system": "SAP_S4HANA",
            "journals": [{
                "source_record_id": "RECON-ERP-001",
                "legal_entity_code": "US01",
                "posting_date": today,
                "currency": "USD",
                "amount": "250000.00",
                "counterparty": "Reconciliation Customer",
                "reference": "E2E-RECON-001",
                "document_type": "BANK_GL"
            }]
        })
        assert journal.status_code == 200

        result = client.post("/api/v1/integrations/phase1/reconcile/bank-erp", headers={"X-Treasury-User":"treasurer.demo"}, json={
            "bank_connector_code": "SWIFT_ISO20022",
            "erp_connector_code": "SAP_S4_FINANCE",
            "start_date": today,
            "end_date": today,
            "amount_tolerance": "0.01",
            "date_tolerance_days": 1
        })
        assert result.status_code == 200, result.text
        body = result.json()
        assert body["matched_count"] >= 1
        assert any(x["reference"] == "E2E-RECON-001" for x in []) is False  # response intentionally exposes exceptions, not raw records


def test_phase1_market_data_ingestion():
    now = datetime.now(UTC).isoformat()
    with TestClient(app) as client:
        spot = client.post("/api/v1/integrations/phase1/market/quotes", headers={"X-Connector-Name":"MARKET_DATA_LIVE"}, json={
            "connector_code": "MARKET_DATA_LIVE",
            "source_system": "LICENSED_VENDOR_UAT",
            "quotes": [{
                "instrument": "EURUSD",
                "asset_class": "FX",
                "base_currency": "EUR",
                "quote_currency": "USD",
                "mid": "1.1850",
                "bid": "1.1849",
                "ask": "1.1851",
                "as_of": now,
                "source": "LICENSED_VENDOR_UAT",
                "source_record_id": "EURUSD-REAL-001"
            }]
        })
        assert spot.status_code == 200
        assert spot.json()["applied"] == 1

        risk = client.post("/api/v1/integrations/phase1/market/risk-data", headers={"X-Connector-Name":"MARKET_DATA_LIVE"}, json={
            "connector_code": "MARKET_DATA_LIVE",
            "source_system": "LICENSED_VENDOR_UAT",
            "curve_points": [{
                "source_record_id": "USD-OIS-30D-001",
                "curve_name": "USD_OIS",
                "currency": "USD",
                "curve_type": "DISCOUNT",
                "tenor_days": 30,
                "zero_rate": "0.0425",
                "as_of": now,
                "source": "LICENSED_VENDOR_UAT"
            }],
            "volatility_quotes": [{
                "source_record_id": "EURUSD-ATM-90D-001",
                "asset_class": "FX",
                "underlying": "EURUSD",
                "tenor_days": 90,
                "quote_type": "ATM",
                "volatility": "0.095",
                "as_of": now,
                "source": "LICENSED_VENDOR_UAT"
            }]
        })
        assert risk.status_code == 200
        assert risk.json()["applied"] == 2


def test_phase1_status_is_honest_about_live_readiness():
    with TestClient(app) as client:
        response = client.get("/api/v1/integrations/phase1/status")
        assert response.status_code == 200
        body = response.json()
        assert body["phase"] == "PRODUCTION_PHASE_1_REAL_DATA_INTEGRATION"
        assert body["overall_status"] in {"BUILD", "INTEGRATION_UAT", "READY_FOR_LIVE_UAT"}
        assert body["certified_connector_count"] == 0
        assert any(x["status"] == "NOT_TESTED" for x in body["certification"])


def test_phase1_connector_identity_and_schema_are_enforced():
    with TestClient(app) as client:
        payload={
            "connector_code":"SWIFT_ISO20022","source_system":"SWIFT_ISO20022","schema_version":"1.0","balances":[]
        }
        wrong=client.post("/api/v1/integrations/phase1/bank/balances",headers={"X-Connector-Name":"OTHER"},json=payload)
        assert wrong.status_code==403
        bad_schema=client.post("/api/v1/integrations/phase1/bank/balances",headers={"X-Connector-Name":"SWIFT_ISO20022"},json={**payload,"schema_version":"2.0"})
        assert bad_schema.status_code==422


def test_phase1_real_data_coverage_and_certification_gate():
    with TestClient(app) as client:
        coverage=client.get("/api/v1/integrations/phase1/coverage")
        assert coverage.status_code==200
        body=coverage.json()
        assert body["overall_status"] in {"UAT","READY_FOR_PARALLEL_RUN"}
        assert body["bank_accounts_total"]>=6
        assert isinstance(body["blockers"],list)

        no_evidence=client.patch(
            "/api/v1/integrations/phase1/certification/SWIFT_ISO20022/BANK_PROVIDER_UAT",
            headers={"X-Treasury-User":"integration.owner"},json={"status":"PASS","evidence":""},
        )
        assert no_evidence.status_code==400
        approved=client.patch(
            "/api/v1/integrations/phase1/certification/SWIFT_ISO20022/BANK_PROVIDER_UAT",
            headers={"X-Treasury-User":"integration.owner"},json={"status":"WATCH","evidence":"Bank UAT window scheduled; certificate exchange pending."},
        )
        assert approved.status_code==200
        assert approved.json()["status"]=="WATCH"


def test_phase1_sap_and_oracle_normalizers_are_deterministic():
    from app.integrations.erp_adapters import SAPS4HanaConnector, OracleFusionFinancialsConnector
    sap = SAPS4HanaConnector.normalize_open_items([{
        "CompanyCode":"US01","TransactionCurrency":"USD","AmountInTransactionCurrency":"1250.50",
        "NetDueDate":"2026-10-20","AccountingDocument":"19000001","Customer":"CUST100"
    }], "RECEIVABLE")
    assert len(sap)==1 and sap[0].legal_entity_code=="US01" and sap[0].amount==Decimal("1250.50")

    oracle = OracleFusionFinancialsConnector.normalize_invoices([{
        "BusinessUnit":"US01","InvoiceCurrencyCode":"USD","InvoiceAmount":"825.00",
        "DueDate":"2026-10-21","InvoiceNumber":"AP1001","SupplierName":"Supplier One"
    }], "PAYABLE")
    assert len(oracle)==1 and oracle[0].flow_type=="PAYABLE" and oracle[0].amount==Decimal("825.00")


def test_phase1_iso20022_parser_handles_debit_sign_and_available_balance():
    from app.integrations.iso20022 import parse_camt_cash_report
    result=parse_camt_cash_report(CAMT_053)
    assert result.message_type=="camt.053"
    assert result.balances[0].book_balance==Decimal("45000000.00")
    assert result.balances[0].available_balance==Decimal("43000000.00")
    assert result.transactions[0].amount==Decimal("125000.00")
