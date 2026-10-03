# MVP-20 — Production Readiness & Five-Agent Architecture

## Five GPT-6 Astra agent teams
1. Liquidity & Funding Agent
2. Market & Derivatives Risk Agent
3. Global Treasury & Tax Agent
4. Risk, Controls & Model Governance Agent
5. Treasury Orchestrator & Decision Agent

Specialist findings are retained, but live LLM reasoning is batched by these five teams to reduce tokens and latency without reducing deterministic risk coverage.

## Production layer
- Explicit production-readiness gate with human release-board authority.
- PostgreSQL/Alembic migration chain through `0020_production_readiness`.
- Backend/frontend Docker references.
- Production compose reference.
- Kubernetes health-probe reference deployment.
- CI pipeline.
- Load-test harness.
- Trusted-host, CORS and HSTS hardening.

## Verification
- 106 backend tests covered across clean-database regression blocks.
- New MVP-15 through MVP-20 tests pass.
- Python compilation passes.
- Alembic fresh migration passes and creates all new tables.
- Frontend TypeScript source check passes using local dependency stubs because frontend packages are not installed in the build runtime.

## Production honesty
The synthetic environment reports `NO_GO`. Live bank certification, ERP UAT, market-data licensing, HSM/KMS, penetration testing, tax/legal sign-off and DR exercises remain real-environment requirements.
