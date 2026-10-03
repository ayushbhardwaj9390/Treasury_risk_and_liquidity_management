# Pilot acceptance scenarios — awaiting enterprise execution

All scenarios are NOT RUN against real providers. These are starting scenarios;
the enterprise reviewers define representative volumes, scope and expected values.
Attach authentic documents and record actual outcomes before marking any PASS.

| Case | Scenario | Required outcome | Owner role |
|---|---|---|---|
| BANK-01 | Bank statement and balance ingestion | Approved account mapping; amounts, currencies, dates and lineage match source | INTEGRATION_OWNER |
| BANK-02 | Duplicate, collision and unmapped account | Idempotent duplicate handling; conflicting/unmapped data quarantined | INTEGRATION_OWNER |
| ERP-01 | AR/AP and journal reconciliation | Approved bank/ERP references reconcile; exceptions remain visible | INTEGRATION_OWNER |
| MARKET-01 | Licensed feed, stale/missing currency | License verified; required currencies covered; stale/missing feed blocks readiness | INTEGRATION_OWNER |
| MODEL-01 | Independent pricing/forecast/risk review | Validator differs from developer; every current model/version covered, limits documented | RISK_MANAGER |
| SECURITY-01 | Expired/wrong issuer token and wrong role | Access denied; no privileged demo-header access | SECURITY_OFFICER |
| SECURITY-02 | Secrets, signing, SIEM and penetration review | Enterprise controls verified; material findings resolved and evidenced | SECURITY_OFFICER |
| PARALLEL-01 | Sustained comparisons across every scope/metric | 60 distinct days, fresh per metric, prescribed variance rules satisfied | GROUP_TREASURER |
| PARALLEL-02 | Small unmatched payment or stale FX | Readiness blocked even when aggregate pass rate exceeds 95% | PAYMENT_OPERATOR |
| TREASURY-01 | Cash, forecast and liquidity decisions | Results match reviewed enterprise reference; human decision boundary retained | GROUP_TREASURER |
| PAYMENT-01 | Maker-checker, dispatch and provider ACK | Unauthorized release denied; actual certified flow reconciles without duplicate dispatch | PAYMENT_OPERATOR |
| ACCOUNTING-01 | Journals and accounting outcomes | Expected postings and references match approved accounting cases | ACCOUNTING_REVIEWER |
| OPS-01 | Representative load and PostgreSQL concurrent halt | Approved capacity met; state changes cannot authorize post-halt execution | OPERATIONS_MANAGER |
| OPS-02 | Restore/failover and alert receipt | Measured RTO/RPO targets met; named on-call recipient receives alert | OPERATIONS_MANAGER |
| OPS-03 | HALT then ROLLBACK rehearsal | Execution blocked in both states; operator restores approved artifact and reconciles ledgers | OPERATIONS_MANAGER |
| TAX-01 | Entity-specific tax treatment | Qualified reviewer approves actual jurisdictional cases | TAX_REVIEWER |
| LEGAL-01 | Contracts, netting and jurisdictional constraints | Qualified reviewer approves applicable documents and constraints | LEGAL_REVIEWER |
| AUDIT-01 | Evidence integrity and access trail | Documents authentic, retained, traceable and independently reviewed | AUDITOR |
| RELEASE-01 | Missing evidence, rejection or changed digest | Go-live denied; previous sign-offs cannot approve changed evidence | GROUP_TREASURER |

For each run record: case ID, scope, expected outcome, actual outcome, PASS/FAIL,
evidence reference and SHA-256, named tester/reviewer, execution time, defects and
resolution. UAT PASS submissions require case records and zero open material defects.
