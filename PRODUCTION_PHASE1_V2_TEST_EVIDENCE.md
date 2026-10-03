# Production Phase 1 v2 Test Evidence

## Dedicated integration/control tests
- `tests/test_production_phase1.py` + `tests/test_production_phase1_v2.py`: **16/16 PASS** on a fresh SQLite database.

Coverage includes:
- ISO 20022 ingestion and lineage
- unmapped-record quarantine
- ERP cash-flow mapping
- detailed bank/ERP reconciliation
- market quote / curve / volatility ingestion
- connector identity and schema enforcement
- real-data coverage and certification evidence controls
- deterministic SAP/Oracle normalization
- default SHADOW authority
- shadow record persistence
- blocked premature ACTIVE promotion
- 10-day parallel-run readiness gate
- data-quality SLA scoring
- accountable quarantine resolution
- parallel-readiness status

## Historical regression samples
Fresh-database blocks verified after the v2 changes:
- Core liquidity/forecast/derivative foundation: **10/10 PASS**
- Agent, model-risk and derivative-control block: **6/6 PASS**
- MVP-7 security + MVP-8 live operations block: **14/14 PASS**
- MVP-15→22 + five-agent architecture block: **13/13 PASS**

The prior Phase-1 v1 release had 122 covered tests across historical + Phase-1 blocks. The full monolithic suite is not claimed as a single-run result here because heavyweight legacy orchestration tests exceed the execution window when run together; regression is therefore intentionally split into fresh-database blocks.

## Migration verification
Clean Alembic upgrade through `0024_parallel_validation`: **PASS**.
- Table count: **65**
- Missing required v2 tables: **0**
- Quarantine resolution actor/timestamp fields: **present**

## Build verification
- Python module compilation: **PASS**
- Frontend TypeScript source verification with local dependency declarations: **PASS**
- Full Next.js bundle: **not claimed**; npm dependency installation is environment-dependent.
