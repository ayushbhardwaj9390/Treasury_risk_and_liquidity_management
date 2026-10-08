# Global Treasury AI — Production Phases 2–4

The company-tools release adds direct XLSX import, daily money/warning review,
manual actual-versus-plan comparisons and authenticated planning/preference drafts.
Scheduled-feed settings report freshness and missing worker configuration explicitly.
See [release notes and availability](RELEASE_NOTES_COMPANY_TOOLS.md).

Production validation candidate: see [release controls and runbooks](docs/PRODUCTION_PHASES_2_4.md).
Production remains blocked until real external evidence and separate human sign-offs pass.

The **Automatic updates** workspace now demonstrates freshly calculated cash,
forecasts, hedge coverage and risk checks from a fictional event feed. No private
data is required. See [dummy automation and its limits](docs/AUTOMATIC_DUMMY_UPDATES.md).

Company setup now supports industry-neutral profiles, pending legal-entity registrations
and staff-role visibility in a dedicated deployment per company. See
[company onboarding and deployment limits](docs/COMPANY_ONBOARDING.md).
The public site is a recorded demo; company saving requires a configured backend and
company sign-in. Pending registrations never activate treasury data or clear go-live gates.

Built on the completed MVP-22 treasury platform. Production Phase 1 starts the transition from controlled/synthetic inputs to governed real-bank, ERP and market-data integration.

Enterprise-oriented multinational **treasury risk and liquidity risk** platform. The application separates deterministic financial calculations, risk models, policy/legal/tax constraints, GPT-6 Astra reasoning, human approvals and external execution.


## Production Phase 1 — Real Data & Integration

### v2: controlled parallel validation
Real provider domains now start in **SHADOW** mode. Bank balances, ERP cash flows and market-risk inputs are staged and compared before they are allowed to become authoritative. Promotion to `ACTIVE` requires complete connector certification, a passing data-quality SLA, a ready parallel-run gate and named human evidence.

Implemented across Phase 1:
- ISO 20022 camt.052/camt.053 cash-report ingestion with transaction extraction.
- Canonical bank, ERP and market-data contracts.
- SAP S/4HANA Finance and Oracle Fusion Financials read-only adapter boundaries.
- External-reference mapping from provider identifiers to internal treasury entities/accounts.
- Source-to-target data lineage with timestamps, schema versions and SHA-256 payload fingerprints.
- Quarantine for unmapped, malformed, duplicate/colliding or unsupported source records.
- Bank-to-ERP detailed reconciliation with explicit exceptions.
- Connector-run telemetry, watermarks, source/target totals and reconciliation state.
- Evidence-based connector certification. A connector is counted as certified only when **all required controls** are PASS.
- Real-data coverage gate for bank balances, ERP cash flows, market currencies and reconciliation quality.
- Connector identity enforcement and production managed-secret/workload-identity boundary.
- SHADOW / ACTIVE / BLOCKED source-authority policies.
- Shadow-data store and promotion controls.
- Data-quality SLA scorecards across timeliness, completeness, validity, uniqueness and reconciliation.
- Incumbent-vs-platform parallel-run observation ledger and readiness gate.
- Accountable quarantine-resolution workflow.

The reference environment deliberately remains **INTEGRATION_UAT**, not production-certified, until real provider credentials, mappings, reconciliation evidence, failover/volume testing and human sign-off are supplied.

## Five-agent operating model

GPT-6 Astra reasoning is consolidated into five senior agent teams. Specialist analytics remain available underneath as deterministic engines and domain capabilities.

1. **Liquidity & Funding Agent** — cash, forecasts, working capital, survival horizon, funding, refinancing and contingency funding.
2. **Market & Derivatives Risk Agent** — FX, rates, derivatives, valuation, hedging, collateral, counterparty and market risk.
3. **Global Treasury & Tax Agent** — cash mobility, pooling, cross-border constraints, intercompany funding, tax-aware routing and legal-entity transferability.
4. **Risk, Controls & Model Governance Agent** — policies, limits, model risk, data quality, reconciliations, screening, security, resilience and auditability.
5. **Treasury Orchestrator & Decision Agent** — compares validated strategies and prepares management decision support.

The five-agent layer never replaces deterministic calculations. It uses validated outputs and has **no approval or execution authority**.

## Core capability stack

### Liquidity and funding
- Multi-entity / multi-currency cash position
- Restricted, committed and trapped cash
- 13-week forecast and stress scenarios
- Structural liquidity ladder
- Intraday liquidity
- Liquidity-at-Risk / Cash-Flow-at-Risk
- Liquidity survival horizon
- Working-capital DSO / DPO / DIO / CCC
- Forecast-vs-actual accuracy and bias
- Contingency funding plans
- Funding concentration and maturity risk
- Debt, covenant and refinancing risk

### Markets and derivatives
- FX residual exposure and hedge coverage
- Interest-rate gap and DV01 proxy
- Curve-based FX forwards, FX options and IRS valuation
- VaR / Expected Shortfall / EaR
- Historical EWMA volatility and dynamic correlations
- Legal close-out netting
- Counterparty PFE and XVA-style sensitivities
- CSA / collateral liquidity and optimization
- Independent Price Verification
- Hedge accounting control boundary

### Global MNC treasury
- Global cash pooling
- Intercompany facilities
- Tax-aware cross-border funding controls
- Transfer-pricing range controls
- Cash mobility and trapped-cash analysis
- **MVP-15 legal-entity liquidity optimizer** using a 90-day entity cash view
- **MVP-15 cross-border constraint graph** with legal, regulatory and tax gates
- No routing through uncleared jurisdictions or transfer structures

### Enterprise integrations — MVP-16
- Canonical bank / ERP / market / TMS / tax connector catalog
- Connector health, latency, error-rate and freshness controls
- Idempotency and reconciliation capability checks
- Retry and circuit-breaker framework
- Canonical connector-envelope contract
- Workload-identity boundary
- Event ledger, checkpoint and replay controls
- External bank acknowledgement separated from internal release status

### Security — MVP-17
- Production OIDC/JWT identity boundary
- RBAC, maker-checker and segregation of duties
- Trusted-host and configurable CORS controls
- Security headers and production HSTS
- Secret-provider, HSM/KMS signer and SIEM integration interfaces
- Payment screening block
- Audit and evidence boundaries
- Environment segregation controls

### Model governance — MVP-18
- Model registry
- Backtesting / benchmark validation records
- Champion-challenger architecture
- Drift monitoring
- Model-validation dashboard
- Independent valuation controls
- No automatic model promotion
- Production decision use blocked where validation is unresolved

### Role workflows — MVP-19
Role-specific investigation workspaces for:
- CFO
- Group Treasurer
- Risk
- Treasury Operations
- Tax
- Audit

Each workspace exposes its own queue and recommended control panels while preserving authenticated human ownership.


### Predictive Treasury Risk Radar — MVP-21
- Governed market-regime classification from approved historical FX returns
- Composite treasury deterioration score clearly separated from statistical probabilities
- Dynamic liquidity/market/funding stress scenarios
- Liquidity breach probability sourced only from the Monte Carlo liquidity engine
- Survival horizon, funding concentration and forecast-bias drivers
- Zero execution authority

### Strategic Treasury Optimization — MVP-22
- Optimal liquidity-buffer planning range
- Explicit operating, tail-risk, intraday, collateral and refinancing components
- Three-year strategic treasury planning
- Fixed/floating debt structure targets
- Policy-constrained FX hedge targets
- Funding concentration targets
- Long-term funding mix targets
- Strategic options retain incomplete-pricing warnings until executable spreads, fees, basis and tax inputs are connected
- Human approval remains mandatory; execution authority is `NONE`

### Production-readiness layer — MVP-20
- Explicit production-readiness gate
- Human release-board deployment authority
- PostgreSQL/Alembic persistence architecture
- Backend and frontend Dockerfiles
- Production compose reference
- Kubernetes readiness/liveness reference deployment
- CI pipeline
- Health/readiness endpoints
- Prometheus-style metrics
- Load-test harness
- DR/RTO/RPO controls

The synthetic reference environment intentionally reports **NO_GO** for production because real bank certification, live ERP reconciliation UAT, production market-data licensing, HSM/KMS configuration, independent penetration testing, country-specific tax/legal sign-off and a full DR exercise cannot be honestly completed inside a synthetic project.

## Key design rules

```text
Data / Market Inputs
        ↓
Deterministic Treasury & Risk Engines
        ↓
Five Astra Agent Teams
        ↓
Policy + Tax + Legal + Model + Security Controls
        ↓
Human Decision / Maker-Checker
        ↓
Release for Execution
        ↓
External Bank / Trading Connector
        ↓
External Acknowledgement + Reconciliation
```

- AI does not create financial values.
- AI does not approve transactions.
- AI does not bypass treasury limits.
- AI does not autonomously trade derivatives.
- Intercompany facilities are not double-counted as new group cash.
- Cash mobility is constrained by legal-entity and jurisdiction rules.
- Economic hedging and hedge accounting remain separate concepts.
- Liquidity, market value, collateral, refinancing and intraday effects remain separately attributable.

## Run locally

Backend:

```bash
cd backend
python -m venv .venv
# activate the environment
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Default demo backend: `http://localhost:8000`

## Database migrations

```bash
cd backend
alembic upgrade head
```

Migration chain remains at `0020_production_readiness`; MVP-21/22 add governed analytics without introducing new persistence tables.

## Tests

```bash
cd backend
PYTHONPATH=. pytest -q
```

MVP-22 regression coverage contains **112 backend tests**, including 6 dedicated MVP-21/22 controls. In this constrained build runtime they were executed in clean-database regression blocks to stay inside the execution window.

## Production deployment warning

This repository is an enterprise-grade reference implementation and pilot foundation, **not a claim that a real MNC can deploy it unchanged into production**. Production requires company-specific data, real provider integrations, security certification, independent model validation, legal/tax approval, UAT, performance testing and controlled change/release management.
