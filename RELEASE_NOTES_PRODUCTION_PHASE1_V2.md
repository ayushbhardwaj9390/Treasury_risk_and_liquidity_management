# Production Phase 1 v2 — Parallel Validation & Source Authority

This release strengthens the real-data integration layer so external feeds can be validated without silently becoming authoritative treasury inputs.

## Added
- Source authority policy per connector/domain: `SHADOW`, `ACTIVE`, `BLOCKED`.
- Default SHADOW posture for bank balances, ERP cash flows, FX spot, yield curves and volatility data.
- Shadow-data store with immutable payload fingerprints and lineage.
- Controlled promotion gate: ACTIVE requires all connector certification controls PASS, latest data-quality SLA PASS, and a READY parallel run.
- Data-quality SLA scoring across timeliness, completeness, validity, uniqueness and reconciliation.
- Parallel-run observation ledger comparing incumbent vs platform outputs with tolerances.
- Parallel-run readiness summary requiring at least 10 observation days and >=95% pass rate.
- Accountable quarantine resolution with actor, timestamp and evidence.
- Real-data coverage now includes accepted SHADOW records, allowing completeness validation before promotion.
- Integration control-plane UI showing source authority and parallel readiness.

## Safety boundary
External UAT/provider data does not modify core treasury balances, cash flows or market-risk inputs while the corresponding source/domain is in SHADOW mode. Promotion is a human-controlled governance action and does not grant payment or trading authority.

## Verification
- 16/16 Production Phase 1 v1+v2 tests pass on a fresh database.
- Additional historical regression blocks: 10/10 core liquidity tests, 6/6 agent/derivative-control tests, 14/14 security/live-operations tests, 13/13 MVP-15→22/five-agent tests.
- Alembic clean upgrade through `0024_parallel_validation` passes.
- Clean migration creates 65 tables; all four v2 tables and quarantine-resolution fields verified.
- Python compilation passes.
- Frontend TypeScript source verification passes using local dependency declarations.

## Remaining real-world evidence
The reference environment is not promoted to ACTIVE because it does not contain real provider UAT credentials, representative parallel-run history, production entitlements, or human certification evidence.
