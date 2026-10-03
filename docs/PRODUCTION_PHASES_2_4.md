# Production Phases 2–4

This release adds code-side readiness controls to the verified Phase 1 v2 baseline.
It is an offline validation candidate, **not certified for production**. No real
bank, ERP, market-data, tax, legal, security or user acceptance approval is seeded.

## Phase 2: validation, security and resilience

`POST /api/v1/production/model-benchmark` calculates deterministic MAE, bias and
challenger MAE from equal-length finite vectors. It does not approve a model.
The independent model validation evidence must name a different developer,
identify the benchmark, record limitations and cover every current registry model
code/version. A model version change blocks the gate until validation is refreshed.
Professional independent validators must validate liquidity, pricing, risk,
predictive models and optimization assumptions on representative enterprise data.

Production startup rejects demo identity, incomplete OIDC, non-HTTPS identity
endpoints, wildcard hosts/CORS, SQLite and disabled security headers. Production
API access requires a signed identity. The new governance endpoints also require
an active provisioned enterprise user and the specific role for each action.
Request bodies are limited to 2 MiB by default, including streamed bodies. The
service generates request IDs and avoids returning database exception details.
HTTP metrics use route templates to limit label cardinality.

The backend image uses a non-root account and a pinned dependency inventory.
The Kubernetes reference adds no privilege escalation, dropped capabilities,
read-only root filesystem, a bounded temporary volume and runtime-default seccomp.
It requires the enterprise `treasury-production-config` secret and production
identity/database configuration; no credentials are supplied. Replace the image
tag with a verified immutable digest during release approval. Container and
cluster behavior still requires target-environment testing.

Infrastructure must still enforce TLS, workload identity, MFA, network policies,
distributed rate limits, database encryption, secrets vault, KMS signing, SIEM
and WORM evidence storage. The current production connector identity deliberately
remains blocked. Do not weaken this boundary to connect a provider.

`scripts/resilience_drill.py` checks a read-only SQLite source using the backup API,
restores to a temporary database, checks integrity, table inventory and identical
bytes, and emits a report explicitly labeled SYNTHETIC/LOCAL_SQLITE_ONLY.
It measures local elapsed time, **not production RTO/RPO**. Real restore/failover
and rollback rehearsal evidence requires measured RTO <=30 minutes and RPO <=5 minutes.

## Phase 3: parallel run, UAT and evidence

Create a release with the exact candidate artifact SHA-256 and a different prior
artifact hash. Use a stable digest of the deployment artifact; the final download
ZIP checksum is a transport checksum and need not be the deployed image digest.
All evidence and observations are scoped to that release.

Evidence records contain kind (REAL/SYNTHETIC), result, external document digest,
reference, scope, recorder, expiry and structured details. This API registers
attestations: document bytes and authenticity must be verified by reviewers in the
enterprise evidence repository. A text reference or hash alone is not certification.
Evidence is append-only through this API. The newest record for each gate wins,
so failed, synthetic or expired replacement evidence blocks earlier passes.
Expiry is mandatory, at most 90 days from submission.

Parallel-run observations cover CASH, FORECAST, FX, LIQUIDITY, PAYMENTS and RISK.
Each declared scope/metric requires 60 distinct observation days in the last 90
days, >=95% pass rate and no variance above 2%. Payment comparisons require exact
agreement on every observation; even a small unmatched payment blocks readiness.
Other metrics have a fixed 0.5% tolerance. A zero incumbent with a
nonzero platform value fails as material. Future dates and duplicate scope/day/
metric records are rejected. Every scope/metric must be current to the previous day;
fresh cash observations cannot mask stale FX or other comparisons.
UAT PASS evidence must contain case IDs, expected and actual outcomes, evidence
digests and zero open material defects. The enterprise reviewer verifies case
coverage and document authenticity before signing.
Only REAL observations contribute to readiness. Phase 1 source coverage,
reconciliation and authority controls must also pass.

Required UAT roles/gates are returned by the release status endpoint. Enterprise
administrators provision named users in `user_accounts`; these privileged roles
are never added to demo accounts automatically. Role changes require the existing
enterprise identity/access-management process, outside the public API.

Sign-offs bind to a SHA-256 of the release evidence and observations. New evidence
invalidates earlier sign-offs. Makers cannot sign their own release. Incomplete
evidence cannot be approved. Rejections, inactive users and role changes block
readiness. Separate role-based approvals include integration, risk, security,
operations, treasury, payments, accounting, tax, legal, audit and CFO.

## Phase 4: release governance and monitoring

States: DRAFT -> PARALLEL -> LIVE -> HALTED or ROLLED_BACK.
A HALTED release can proceed to ROLLED_BACK; both states keep execution blocked.
An independent Group Treasurer must perform GO_LIVE. All evidence, Phase 1
controls and sign-offs are re-evaluated at that point. A unique database index
prevents two LIVE releases; row locks serialize mutations on PostgreSQL.
SQLite is solely for development/testing, not a concurrent production control store.

Set `PRODUCTION_RELEASE_ID` to the intended release. Production readiness,
transaction release, execution-message creation and dispatch re-evaluate that
release. Missing, halted, rolled-back or newly invalid evidence disables execution.
The locked release read refreshes any cached state, and execution uses the state
from that same governance snapshot to avoid retaining a pre-halt LIVE decision.
`/health/ready` checks service/database availability so that authenticated reviewers
can reach governance APIs before go-live. `/health/production` separately returns
503 until an approved LIVE release exists; operational health is not certification.
Monitoring exports `treasury_production_release_ready`; example Prometheus rules
are in `deploy/production-alerts.yml`. Alert routing and receipt must be rehearsed
and signed off in the real environment.

HALT/ROLLBACK immediately disables this release's execution authorization and
records actor/reason and the previous artifact hash. **It performs no deployment,
database downgrade, payment cancellation or real provider restore.** Operators
must execute the runbook below and attach real rehearsal evidence before launch.

## Operator go-live and recovery runbook

1. Build immutable backend/frontend artifacts; record digests, dependency inventory,
   scan reports, migration evidence and approved deployment scope.
2. Obtain all real evidence and role sign-offs against the current evidence digest.
   Confirm no open material reconciliation, security, UAT or model defects.
3. Back up managed databases and verify a restorable snapshot. Apply additive
   migrations through 0025 in staging, then the approved production change window.
4. Confirm previous application compatibility with the additive schema. Deploy
   read-only/shadow first, configure the candidate release ID and rehearse alerts.
5. Have the independent treasurer record GO_LIVE only after review. The operator
   deploys the approved artifact, verifies health/readiness and enables the
   separately certified external connector. Existing maker-checker controls remain.
6. On failure, HALT first. Quiesce connector dispatch, preserve ledgers and inventory
   in-flight messages. Obtain provider ACK/status and reconcile before any replay.
7. Record ROLLBACK and deploy the recorded previous artifact through the approved
   platform. Restore data only using the approved recovery plan; preserve all
   transactions since backup. Do not blindly downgrade schema or resend payments.
8. Verify restored health, balances, execution ledger and bank/ERP reconciliation.
   Record measured recovery point/time and evidence. A fresh governed release and
   new approval cycle are required before enabling treasury execution again.

## Boundaries preserved

The five GPT-6 Astra senior teams and token-efficient routing remain unchanged.
No new LLM call, agent execution right or autonomous payment/trading capability
is introduced. Existing deterministic treasury engines remain authoritative.
Local regression evidence cannot satisfy external certification gates.

## Unavailable external evidence

Bank/SWIFT and ERP UAT; licensed market feeds; independent model validation;
penetration testing; real SSO/MFA, vault/KMS/SIEM; production load/failover/restore;
monitoring delivery; rollback rehearsal; treasury/payment/accounting UAT;
tax/legal validation; audit and executive sign-off are all outstanding until
actual enterprise evidence is recorded and independently reviewed.
