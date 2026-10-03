# Production Phase 1 — Real Data & Integration

## Objective
Move Global Treasury AI from synthetic/demo inputs to governed enterprise data without allowing unverified source data to silently influence execution-critical treasury decisions.

## Phase 1 scope

### Banking
- ISO 20022 cash-report ingestion for camt.052 and camt.053.
- camt.054 transaction-notification parsing without pretending it is a balance statement.
- Canonical bank balance and transaction APIs.
- External bank-account mapping to internal treasury accounts.
- Idempotency collision controls.
- Quarantine for unmapped accounts, currency mismatch, invalid schema or inconsistent replay.
- Bank-to-ERP detailed reconciliation.

### ERP
- Canonical AR/AP cash-flow ingestion.
- Canonical ERP journal ingestion for detailed reconciliation.
- SAP S/4HANA read-only OData adapter boundary.
- Oracle Fusion Cloud Financials AR/AP REST adapter boundary.
- External company-code/business-unit mapping to internal legal entities.

### Market data
- Canonical FX spot ingestion.
- Yield-curve point ingestion.
- Volatility quote ingestion.
- Source timestamp and source-system lineage.
- Existing stale-feed and primary/secondary failover controls remain in force.

### Control plane
Every accepted production-style record carries:
- connector code;
- source system;
- source object and source record ID;
- payload SHA-256;
- schema version;
- source timestamp;
- target table/record;
- ingestion timestamp;
- reconciliation status.

Rejected records are retained in `integration_quarantine`; they are not silently discarded or coerced.

## Production safety rules
1. Connector identity must match `connector_code` on ingestion writes.
2. Canonical contract version is validated before ingestion.
3. Unmapped legal entities or bank accounts are quarantined.
4. Replaying the same source record with a different payload is an idempotency collision and is quarantined.
5. Real-data coverage is measured separately from connector configuration.
6. Certification `PASS` requires human evidence.
7. Credentials are never stored in the treasury database.
8. Production use refuses development-style connector identity and environment-secret shortcuts.
9. AI remains downstream of deterministic ingestion, mapping, reconciliation and control logic.

## Real-data coverage gate
`GET /api/v1/integrations/phase1/coverage` reports:
- bank-account real-data coverage;
- open ERP cash-flow real-data coverage;
- fresh market-currency coverage;
- detailed bank-to-ERP reconciliation pass rate.

The reference thresholds for moving to a parallel-run stage are:
- >=95% bank-account coverage;
- >=90% ERP cash-flow coverage;
- >=95% required-currency market-data coverage;
- >=95% reconciliation pass rate.

These are rollout gates for the reference platform, not regulatory thresholds.

## Connector certification
A connector is not production-ready merely because an API call succeeds. Certification controls cover authentication, schema validation, idempotency, reconciliation, provider UAT, volume/failover and entitlements.

`PATCH /api/v1/integrations/phase1/certification/{connector}/{control}` requires authenticated treasury identity. A PASS cannot be recorded without evidence.

## Current external standards used by the reference architecture
- SWIFT CBPR+ / ISO 20022 is the basis for cross-border payment and cash-report integration. SWIFT states that the MT/ISO 20022 coexistence period for cross-border payment instructions ended on 22 November 2025. The 2026 roadmap also removes unstructured postal addresses for most CBPR+ messages in November 2026; payment-instruction integration must therefore be validated against the current usage guidelines before go-live.
- SAP S/4HANA integration uses documented finance APIs, including the Journal Entry Item read service and Receivables Management APIs. Customer-specific communication arrangements and field extensions must be mapped in UAT.
- Oracle Fusion Cloud Financials integration uses the documented Financials REST layer, including Receivables Invoices and Payables Invoices resources. Customer-specific security privileges and business-unit mapping must be validated in UAT.

## Source references
- SWIFT, ISO 20022 for Financial Institutions: https://www.swift.com/standards/iso-20022/iso-20022-financial-institutions-focus-payments-instructions
- SWIFT, ISO 20022 implementation FAQ: https://www.swift.com/standards/iso-20022/iso-20022-faqs/implementation
- SAP Help, APIs for Receivables Management: https://help.sap.com/docs/SAP_S4HANA_CLOUD/4f22209d1f5d4bd79c4a55017608b51b/b448d39b85dd4da6baf28e8c818f0e53.html
- SAP Help, Journal Entry Item - Read: https://help.sap.com/docs/SAP_S4HANA_CLOUD/b978f98fc5884ff2aeb10c8fdeb8a43b/8aa29c6ac8234f9a9b975b3900aa002d.html
- Oracle Fusion Cloud Financials REST API: https://docs.oracle.com/en/cloud/saas/financials/26b/farfa/index.html

## What is deliberately not claimed
- No bank/SWIFT provider has been certified in this reference environment.
- No SAP or Oracle customer tenant is connected here.
- No licensed market-data entitlement is bundled.
- No real company data or credentials are included.
- No production payment or derivative execution is enabled by this phase.
