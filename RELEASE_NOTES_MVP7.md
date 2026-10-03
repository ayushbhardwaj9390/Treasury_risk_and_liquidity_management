# MVP-7 Release Notes — Institutional Treasury Risk Layer

## New quantitative engines
- Curve-based FX forward valuation
- Garman-Kohlhagen FX option valuation
- Discount-curve IRS valuation
- Monte Carlo Liquidity-at-Risk / Cash-Flow-at-Risk
- Legal close-out netting engine
- Collateral funding optimization
- Champion/challenger model comparison
- Operational resilience status engine

## New enterprise infrastructure
- PostgreSQL-ready connection pooling
- Alembic migration framework
- Production OIDC/JWT identity boundary
- Production transaction idempotency requirement
- Request IDs and security headers
- Readiness endpoint
- Prometheus-style HTTP metrics
- Retry and circuit-breaker connector runtime
- Idempotent execution connector contract with acknowledgement model

## Agent layer
Six new specialist agents bring the runtime to 35 agents:
1. Institutional Pricing & Valuation Agent
2. Liquidity-at-Risk Agent
3. Legal Netting & Counterparty Agent
4. Collateral Optimization Agent
5. Champion-Challenger Model Agent
6. Operational Resilience & Security Agent

## Demo risk results
Synthetic inputs intentionally demonstrate:
- material model-vs-book valuation differences requiring review
- non-zero 13-week liquidity tail risk
- one legal netting set held at gross exposure pending legal review
- a collateral call with identified same-currency funding capacity
- challenger performance comparison without automatic promotion
- one Tier-1 operational-resilience remediation item

## Verification
- 50/50 backend tests passing
- Python compilation passing
- frontend TypeScript checking passing
- clean database rebuild tested

## Important
All market, tax, legal and company data in the demo are synthetic. Built-in valuation and risk methodologies require independent validation before production use. The repository does not execute bank payments or derivative trades.
