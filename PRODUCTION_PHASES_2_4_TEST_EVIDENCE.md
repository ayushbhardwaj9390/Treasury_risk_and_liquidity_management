# Production Phases 2–4 verification — 3 October 2026

## Scope and baseline

The downloaded Phase 1 v2 archive matched SHA-256
`657e8d7d263bf6897825c56800e44e94242a5a0bf73976f25826b6cc853a9eb9`.
It was extracted into a separate working folder. Synced `sources/` was untouched.
All verification used local synthetic/demo data, no real external credentials.

Environment: Windows, bundled Python 3.12, Node.js, pnpm 11.19.0.
Backend patched versions: FastAPI 0.142.2, Starlette 1.7.0, pytest 9.1.1.
Exact dependency versions are recorded in `backend/requirements-lock.txt` and
`frontend/pnpm-lock.yaml`.

## Test results

| Verification | Observed result |
|---|---|
| Revision 2 complete backend regression run | 176 passed in 320.24 seconds; 1 TestClient deprecation warning |
| Revision 2 governance regressions | 25 passed; five added cases first reproduced the previous failures |
| Revision 2 Python compile, frontend TypeScript and clean migration/drift checks | PASS; migration head 0025, no new upgrade operations |
| Revision 2 baseline preservation checks | Routing, orchestrator and selected liquidity/FX/derivative/optimization engines match baseline bytes |
| Historical regression suite before dependency upgrade | 112 passed |
| Phase 1 + new governance/security suite before dependency upgrade | 43 passed |
| Full backend suite on patched dependencies | 153 passed; 2 obsolete release-version assertions failed |
| Corrected release-version assertions + independent pricing benchmarks | 18 passed (2 corrected assertions + 16 new benchmark cases) |
| Final governance/security suite after readiness separation | 27 passed |
| Availability vs production gate, auth and request-size focused test | 1 passed |
| Python compile checks for application, migrations, tests, scripts | PASS |
| Frontend TypeScript check, restored original configuration | PASS |
| Next.js optimized production build | PASS |
| Clean Alembic migration to 0025 and metadata drift check | PASS; 70 tables, no upgrade operations detected |
| Upgrade of original populated 0024 baseline to 0025 | PASS; 65 -> 70 tables, 6 existing users preserved |
| Local SQLite backup/restore | PASS; integrity `ok`, identical restored bytes, 70 tables |
| Local 10-thread API smoke/load run | 100 requests, 0 failures; p95 10,370.319 ms |
| Backend pinned dependency audit after remediation | No known vulnerabilities reported |
| Frontend dependency audit | No known vulnerabilities reported |
| Deployment and alert YAML syntax | Parsed successfully |

Revision 2 verified all **176 backend cases in one complete final run**. The
previous revision's 171 cases were verified across the full and focused runs above.
The two full-run failures were assertions of `0.9.0` after the application was
intentionally released as `0.10.0`; both corrected assertions passed on rerun.
The added pricing tests independently compare discounted forward cashflows and
FX option values using SciPy normal probabilities over tenors, buy/sell directions,
call/put types and volatility levels. They do not certify a valuation library.

Five revision 2 regressions cover stale FX hidden by fresh cash observations,
small unmatched payments despite a passing aggregate rate, rollback after HALT,
execution using the locked snapshot state, and refreshing cached release state.
Each test failed before its fix and passed afterward. Every scope/metric must now
be fresh; every payment observation must agree; HALTED can transition to ROLLED_BACK
while execution remains blocked. PostgreSQL concurrency still requires target-
environment verification; the local cached-state tests are not a concurrency certification.

The final test runner emits a deprecation warning about TestClient's `httpx`
integration. It does not affect the observed passing results. Migration testing
was on SQLite, not a real managed PostgreSQL instance. Docker is unavailable in
this workspace; hardened Docker/Kubernetes templates were not built/deployed.

## Security remediation

The first backend dependency audit flagged the baseline pytest and Starlette
versions. FastAPI, Starlette and pytest were upgraded together to compatible
patched versions, the exact inventory was refreshed, and the audit was rerun.
See `BACKEND_DEPENDENCY_AUDIT.json` and `frontend/frontend-audit.json`.
These are dependency advisory scans, not penetration tests, DAST or certification.
A focused source search found no use of unsafe `eval`/`exec`, `pickle.loads`,
`shell=True`, `verify=False`, private-key PEMs or matching OpenAI key patterns
in the inspected application/frontend/script sources. This is not a comprehensive
secret scanner or proof of absence of vulnerabilities.

## Negative controls verified

Missing/synthetic/failed/expired evidence blocks readiness; release makers cannot
self-approve; wrong roles cannot register evidence; independent model validators
must differ from the recorded developer; changed model versions invalidate model
coverage; changed evidence invalidates sign-offs; inactive signers and human
rejections block approval. Future observations are forbidden, zero-baseline
differences are material, missing metrics, stale data and material variances block
parallel readiness. UAT defects and failed measured recovery targets reject PASS.
Incomplete releases cannot go live. Live evidence freezes. Rollback records the
prior artifact and disables execution without claiming a deployment occurred.
Signed tokens with wrong issuer/audience, expiry, subject or signature are rejected.
Production demo-auth startup is rejected. Requests above the configured body
limit are rejected. Service availability and production approval are separate.

## External evidence remains BLOCKED

Synthetic energy execution supplement: five scenarios passed independent opening
balance and weekly cashflow/closing/headroom checks through unchanged treasury
engines. The incomplete-release execution guard denied authorization. The runner
compiled successfully. Results and limitations are in `pilot/ENERGY_PILOT_REPORT.md`
and `pilot/ENERGY_PILOT_RESULTS.json`. No external evidence gate was satisfied.

Pilot handover supplement: both planning JSON files parse successfully. The
17 gate names/owner roles and required sign-off roles match the runtime policy.
All evidence hashes, references and named approvers remain empty. Synthetic
planning assumptions are separate from the unassigned enterprise scope. Runtime
code is unchanged since the complete 176-case revision 2 run; it was not rerun
for this documentation-only supplement.

No bank/ERP certification, licensed market-data verification, independent human
model approval, enterprise identity/KMS/SIEM verification, penetration testing,
production load/failover, treasury/payment/accounting UAT, tax/legal validation,
audit approval or executive approval was obtained or fabricated.

The local load result is a smoke test and exposes slow tail latency. Production
capacity targets, representative volume, provider failure/recovery, alert receipt,
PostgreSQL concurrency and transaction-safe rollback must be measured in the target
enterprise environment before their evidence gates can pass.

Packaging verifies archive integrity and every source-file SHA-256 against the
included `RELEASE_MANIFEST.json`. The external `.sha256` file identifies the ZIP.
Databases, secrets, dependencies, build output and caches are excluded.
