# Enterprise pilot handover

Status: PREPARATION COMPLETE; EXTERNAL SETUP BLOCKED. This folder is a planning
pack, not a certification, approval or deployment. No live feeds are connected.

User-authorized planning assumptions: a Shell-inspired fictional oil and petroleum
products business, fictional UK and Singapore entities, USD reporting, USD/GBP/SGD
transactions, simulated bank accounts, an SAP S/4HANA adapter boundary and local
synthetic rehearsal. These do not describe Shell's actual operations or systems.
They are recorded separately in `assumed_rehearsal_scope`; the actual enterprise
scope remains unassigned. No actual SAP tenant or bank connectivity is implied.
`ENERGY_DEMO_SCENARIO.json` supplies fictional opening balances, crude purchases,
product receipts, operating costs and stress cases. The five local cash-forecast
scenarios have been executed; see `ENERGY_PILOT_REPORT.md` and the detailed results
JSON. This does not establish commodity valuation or real enterprise UAT.

## 1. Assign the pilot

Complete `PILOT_SCOPE.json` with the actual legal entities, bank accounts, ERP
company codes, currencies, incumbent system, environment and accountable owner.
Set capacity targets before measuring performance. Leave unknown values unassigned.
Use account identifiers approved for this repository; store credentials exclusively
in the enterprise secret manager, never in these files.

The scope worksheet does not configure runtime controls. Source authority must
also be verified in the application's Phase 1 policies. Keep feeds in SHADOW and
dispatch disconnected until their separate certification and release gates pass.

## 2. Provision and verify the environment

The platform team supplies managed PostgreSQL, HTTPS endpoints, OIDC issuer,
audience and JWKS, exact allowed hosts/CORS origins, secrets vault/workload
identity, execution signing, SIEM and an evidence repository. Use the existing
deployment manifests as references; replace image tags with verified digests.
Do not use demo-header identity or SQLite for enterprise production.

Build and scan the artifacts in the target environment. Rehearse migration to
0025 on a restored staging database; verify data counts and recovery. Confirm
database connectivity via `/health/ready`. A blocked `/health/production` is
expected before a fully approved LIVE release. Verify unauthorized requests fail.

The integration owner obtains provider sandbox/UAT access and verifies schemas,
account mappings, payload lineage, duplicates, quarantine and reconciliation.
Production connector identity currently remains blocked; provider-specific
authentication/certification work must be completed against the actual provider.
An adapter boundary alone does not establish connectivity.

## 3. Execute the acceptance scenarios

Use `UAT_SCENARIOS.md` as a starting set, expanded for the approved entity and
provider scope. Record expected and actual outcomes, case IDs, defect severity,
reviewer and authentic evidence documents. Synthetic demonstrations remain
SYNTHETIC and cannot satisfy production gates.

Collect release-scoped REAL comparisons for CASH, FORECAST, FX, LIQUIDITY,
PAYMENTS and RISK for every declared scope. Each needs 60 distinct days within
90 days and data through the previous day. Non-payment tolerance is 0.5%, pass
rate at least 95%, and no material variance above 2%; every payment must match.
Investigate failures without rewriting historical observations.

## 4. Obtain evidence and approvals

`EVIDENCE_REGISTER.json` lists the 17 required gates and their exact owner roles.
Assign actual people using the enterprise access-management process. Keep the
release maker separate from approvers and the model developer separate from the
independent validator. CFO sign-off is required in addition to the gate-owner roles.

The register is not imported into the application. Authorized reviewers register
verified evidence through `/api/v1/production/releases/{id}/evidence`, then read
the release snapshot and sign its current evidence digest through `/signoffs`.
Create the release using actual candidate and prior artifact hashes. Never use
invented hashes, documents, expiry dates or approvers. Changed evidence requires
fresh sign-offs. Follow `docs/PRODUCTION_PHASES_2_4.md` for API controls and recovery.

## 5. Rehearse and decide

Measure representative capacity, provider outages, PostgreSQL concurrency, alert
receipt, restore/failover and rollback. Recovery targets are RTO <=1800 seconds
and RPO <=300 seconds. Local SQLite recovery and local load reports do not meet
these enterprise evidence requirements. Preserve payment ledgers and reconcile
in-flight messages before replay; HALT/ROLLBACK do not cancel or restore payments.

Only the independent treasurer can record GO_LIVE after all blockers clear.
Operators perform the separately approved deployment. Until then, execution
remains blocked. No deployment or live activation has been performed here.
