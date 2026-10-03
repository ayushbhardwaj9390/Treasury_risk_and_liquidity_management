# Global Treasury AI — Project Status: Production Phases 2–4

## Current release — 3 October 2026

The synthetic energy pilot has now executed five scenarios through the unchanged
liquidity/forecast engines, with independent cash-arithmetic checks passing.
Delayed receipts and increased costs expose interim buffer shortfalls; the
combined case reaches USD 6.71 million. Incomplete-release execution was denied.
See `pilot/ENERGY_PILOT_REPORT.md`. Real enterprise testing remains outstanding.

Enterprise pilot preparation now includes `pilot/START_HERE.md`, an unassigned
scope worksheet, all 17 blocking evidence gates with required roles, and 19 UAT
starting scenarios. No enterprise credentials, actual approvers or deployment
environment have been provided; no real-provider tests or live activation occurred.

Revision 2 closes five regression cases around per-metric freshness, unmatched
payments, rollback after halt, and execution decisions using refreshed locked
release state. The deployment status remains blocked by external evidence.

The code-side validation candidate adds independent model benchmarking, model/version
coverage gates, production security hardening, release-scoped UAT and parallel-run
evidence, role sign-offs, controlled go-live/halt/rollback, execution gating and
production monitoring. Migration head is `0025_production_governance`.

**Production status: BLOCKED pending real external evidence and human approvals.**
No provider, tax/legal, model, security, UAT or executive certification is claimed.
The five senior GPT-6 Astra teams, deterministic engines and human execution
boundaries are preserved. See `docs/PRODUCTION_PHASES_2_4.md` for controls and
runbooks, and `PRODUCTION_PHASES_2_4_TEST_EVIDENCE.md` for measured verification.

Earlier Phase 1 history follows; its readiness percentages are historical estimates,
not certification or evidence of this release's deployment readiness.


## Production Phase 1 progress

The build has entered **Real Data & Integration**. The platform now has governed ingress and reconciliation plumbing for external treasury data rather than relying only on synthetic seed data.

Completed:
- ISO 20022 cash reporting ingestion
- canonical bank / ERP / market contracts
- SAP S/4HANA and Oracle Fusion adapter boundaries
- external ID mappings
- lineage and payload fingerprints
- quarantine and idempotency collision controls
- detailed bank-to-ERP reconciliation
- real-data coverage metrics
- evidence-based connector certification
- connector identity / schema enforcement
- migration `0023_real_data_integration`
- migration `0024_parallel_validation`
- SHADOW/ACTIVE/BLOCKED source-authority controls
- parallel-run evidence and data-quality SLA gates
- governed source promotion and quarantine resolution

Current phase status: **INTEGRATION_UAT / PARALLEL_VALIDATION**. Real provider domains remain in SHADOW mode until connector certification, data-quality SLAs and representative parallel-run evidence pass. No connector or data domain is treated as production-authoritative merely because an adapter exists.

## Overall position

The planned MVP-1 through MVP-22 architecture is now implemented as a coherent treasury-risk platform.

Estimated completion against the **designed application scope**:
- Treasury and liquidity functional architecture: **~97%**
- Risk/derivatives/model-control architecture: **~95%**
- Enterprise pilot readiness with controlled/synthetic data: **~90%**
- Live-MNC production readiness: **~60%**, because external systems, production data, security certification and jurisdiction-specific approvals are environment-dependent and cannot be fabricated.

These percentages are engineering estimates, not certifications.

## Completed through MVP-20

### MVP-15 — Legal-entity liquidity and cross-border constraints
- 90-day projected legal-entity liquidity deficits
- Transferable-surplus routing
- Legal/regulatory/tax route graph
- Approved-route caps and estimated withholding cost
- Blocked and unresolved funding needs stay visible
- Zero execution authority

### MVP-16 — Enterprise integration layer
- Bank / ERP / market / TMS / tax connector catalog
- Canonical connector contract
- Idempotency / reconciliation capability controls
- Freshness, latency and error-rate controls
- Retry and circuit breaker
- Event ledger / watermark / replay architecture

### MVP-17 — Security hardening
- OIDC/JWT production identity boundary
- RBAC and maker-checker
- Trusted hosts, configurable CORS and security headers
- HSM/KMS, secret-provider and SIEM interfaces
- Environment segregation controls
- Explicit security evidence status

### MVP-18 — Independent model governance
- Model registry and validation records
- Backtest / benchmark / stability design
- Champion-challenger governance
- Drift monitoring
- IPV and valuation-control framework
- No automatic model promotion

### MVP-19 — Role-specific operating model
- CFO workspace
- Group Treasurer workspace
- Risk workspace
- Treasury Operations workspace
- Tax workspace
- Audit workspace
- Investigation queues and ownership

### MVP-20 — Deployment and production gate
- PostgreSQL-ready persistence
- Alembic migrations through `0020_production_readiness`
- Docker references
- Kubernetes health probes
- CI pipeline
- Metrics and readiness endpoints
- Load-test harness
- Explicit GO / NO_GO deployment gate
- Human release-board authority


### MVP-21 — Predictive Treasury Risk Radar
- Dynamic market-regime classification from approved history
- Governed deterioration score, distinct from probability models
- Dynamic downside and combined stress scenarios
- Treasury-driver attribution across liquidity, survival, funding, market regime and forecast bias
- No execution authority

### MVP-22 — Strategic Treasury Optimization
- Treasury liquidity-buffer planning range
- Multi-year funding / fixed-floating / FX hedge / concentration strategy alternatives
- Explicit missing-executable-pricing control
- Human approval boundary preserved
- Five-agent Astra architecture retained with deterministic engines underneath

## Five-agent architecture

Astra calls are now consolidated into five top-level teams rather than calling every specialist individually:
1. Liquidity & Funding
2. Market & Derivatives Risk
3. Global Treasury & Tax
4. Risk, Controls & Model Governance
5. Treasury Orchestrator & Decision

All underlying specialist calculations remain intact. This reduces token use and latency without reducing treasury/risk coverage.

## What still requires a real MNC environment

1. Real bank/SWIFT connectivity and bank certification.
2. Real ERP/TMS integrations and end-to-end reconciliation UAT.
3. Licensed market-data feeds and production entitlements.
4. Actual company cash history, customer payment history, facilities, covenants, derivative confirmations and CSA terms.
5. Country-by-country tax, exchange-control and legal validation.
6. Independent model validation using company data.
7. HSM/KMS configuration and enterprise secret manager.
8. SIEM/SOC integration and penetration testing.
9. Production PostgreSQL HA cluster and backup/restore evidence.
10. Full DR/failover exercise and measured RTO/RPO.
11. Load/soak testing against the target infrastructure.
12. Treasury-professional UAT and final governance sign-off.

## Current production gate

The reference environment deliberately returns **NO_GO**. This is correct behavior: missing external evidence is treated as a blocker rather than silently assumed to exist.
