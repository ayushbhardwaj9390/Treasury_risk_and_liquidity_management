# Global Treasury AI Architecture — MVP-8

## Control philosophy

```text
Authoritative source systems
(Banks / ERP / market data / approved tax-policy content)
                         ↓
                Connector contracts
                         ↓
       Freshness + schema + reconciliation controls
                         ↓
              Deterministic engines
                         ↓
              Specialist agents
                         ↓
             Model Risk Challenger
                         ↓
      Policy / tax / pre-trade hard controls
                         ↓
          GPT-6 Astra synthesis (optional)
                         ↓
         Maker-checker human approval
                         ↓
      Independent execution-release role
                         ↓
          External execution connector
                         ↓
                Audit evidence
```

## Trust boundaries

### Deterministic calculation boundary
LLMs do not create bank balances, FX conversions, forecasts, derivative marks, tax rates, limits, collateral calls, covenant results or approval states.

### AI boundary
GPT-6 Astra may explain, challenge, compare scenarios and draft recommendations. It receives compact validated outputs plus specialist findings. It cannot bypass a failed control or approve/release a transaction.

### Execution boundary
The code reaches `RELEASED_FOR_EXECUTION` only. No bank/payment connector is called in the demo. Production execution must be an independently authenticated, idempotent integration with acknowledgements and reconciliation.

### Identity boundary
Development uses `X-Treasury-User` as an identity adapter. Production must replace it with SSO/OIDC/JWT claims. Identity is never accepted from transaction payload data.

## Liquidity taxonomy

1. **Operating liquidity**: deployable cash plus durable committed funding after minimum buffers.
2. **Transferable liquidity**: legal-entity surplus movable after local, legal, tax and operating constraints.
3. **Collateral liquidity**: cash reserved for current and stressed derivative margin calls.
4. **Execution liquidity**: liquidity supported by fresh/reconciled data and available at the time a transaction is released.

The system keeps these concepts separate to prevent double counting.

## Transaction lifecycle

```text
DRAFT / proposal request
        ↓
Deterministic pre-trade controls
        ↓
CONTROL_FAILED  ← any hard block
        or
PENDING_APPROVAL
        ↓
Independent L1 approval
        ↓
PARTIALLY_APPROVED (for material transactions)
        ↓
Group Treasurer approval where required
        ↓
APPROVED
        ↓
Controls re-performed at release time
        ↓
Independent Payment Operator
        ↓
RELEASED_FOR_EXECUTION
```

Maker, approver and releaser cannot collapse into the same actor.

## Deterministic engine domains
- global liquidity and multi-currency consolidation
- 13-week cash forecasting
- operating stress and reverse stress
- cash mobility / trapped cash
- cash pooling
- intercompany funding and configured tax/TP controls
- FX exposure and hedge coverage
- derivatives / MTM ingestion
- counterparty exposure / simplified PFE
- interest-rate risk
- market-risk liquidity overlay
- CSA collateral liquidity
- refinancing and covenant risk
- market-data freshness
- connector freshness
- reconciliation gating
- pre-trade transaction controls
- maker-checker and segregation of duties
- hedge-accounting documentation/effectiveness control

## Tax boundary
Tax rules are effective-dated, versioned and source-tagged. `REVIEW_REQUIRED` tax content is not treated as executable advice. Cross-border funding is blocked until tax review is approved.

## Connector design
`app/integrations/contracts.py` defines bank, ERP and market-data contracts independently of vendor implementation. Production adapters must add:
- authentication and secrets rotation
- schema/version validation
- idempotency and replay protection
- retries/circuit breakers
- event timestamps and source IDs
- observability and alerting
- acknowledgements and reconciliation IDs

## Agent operating modes
- **DETERMINISTIC**: no LLM usage
- **SELECTIVE**: material specialists only
- **FULL**: deep review across represented specialists

Selective mode is the default to limit cost and unnecessary token consumption.

## MVP-6 predictive intelligence layer

MVP-6 adds a governed ML layer without moving financial truth into the LLM. Payment behaviour is modeled with deterministic scikit-learn pipelines; validation, drift, fingerprints and registry status are persisted independently. Intraday liquidity, anomaly detection, IPV and integrated scenario calculations feed specialist agents, while GPT-6 Astra remains an optional interpretation layer.

Execution-relevant order remains: source data -> validation/reconciliation -> deterministic/ML engines -> model governance -> specialist agents -> policy/screening controls -> human approvals -> external execution boundary.


## MVP-7 institutional risk layer

### Valuation architecture
Pricing inputs are stored separately from trade records. Governed curve points, volatility quotes and derivative terms feed deterministic FX-forward, Garman-Kohlhagen FX-option and IRS valuation functions. Model values remain distinct from book MTM and IPV.

### Probabilistic liquidity risk
The LaR/CFaR engine runs a seeded Monte Carlo mixture of collection realization, payable pressure, facility availability and collateral demand. It reports percentiles, breach probability and tail funding need. Percentiles are not represented as guaranteed maxima.

### Legal netting
Counterparty netting is recognized only when the configured legal opinion is `APPROVED` and close-out netting is enforceable. Otherwise exposure remains gross. CSA collateral is applied only after the legal-netting decision.

### Model governance
Champion and challenger models are compared on holdout MAE and Brier score. Improvement can trigger independent validation review, but automatic production promotion is disabled.

### Production technology boundary
- PostgreSQL-ready pooling and Alembic migration chain
- OIDC/JWT verifier boundary for production identity
- production write idempotency requirement
- request IDs, no-store/security headers, readiness probe and metrics
- RTO/RPO and DR-test inventory
- retry/circuit-breaker connector runtime
- execution connector contract requires idempotency key and provider acknowledgement

Development still uses synthetic data and SQLite. No bank instruction is submitted by the repository.

## MVP-8 live event architecture

MVP-8 adds an immutable treasury event ledger in front of mutable current-state projections. Bank, ERP, market and execution acknowledgement events pass through connector identity, idempotency, schema/version and sequence controls before they can update projection tables.

A duplicate event with identical content is safe. Reuse of an idempotency key for different content is a control failure. Out-of-order bank balances and market quotes are quarantined rather than allowed to overwrite a newer state.

The continuous monitor is deliberately side-effect constrained: it may calculate risk and create/refresh alerts but cannot create a transaction proposal or change an approval/execution state.

Internal `RELEASED_FOR_EXECUTION` is separated from external execution messaging. A released proposal is wrapped in an integrity-controlled message, placed into `QUEUED`, handed to the connector boundary as `SENT`, and only becomes `ACKNOWLEDGED` or `REJECTED` through a provider acknowledgement.

## MVP-9 optimization and decision-intelligence layer

MVP-9 sits **above** the deterministic treasury/risk stack and **below** human approval. It does not replace pricing, exposure, liquidity, tax, legal, policy or execution controls.

```text
Validated treasury state
        ↓
Liquidity / exposure / pricing / LaR engines
        ↓
Optimization engines
  ├─ hedge portfolio
  ├─ contingency funding
  ├─ cash-pool allocation
  └─ multi-factor scenario search
        ↓
Specialist optimization agents
        ↓
Treasury Decision Committee Agent / Astra synthesis
        ↓
Human decision and existing maker-checker workflow
```

### Optimization controls
- Portfolio hedge optimization starts from mapped business exposure and policy hedge bands. Unmatched derivatives are never used as a reason to add risk.
- Hedge transaction costs are explicit request assumptions. They are not represented as live market quotes.
- Intercompany facilities are legal/funding structures around existing group liquidity and are not counted again as new group cash.
- External committed facilities can provide contingency capacity, but the engine refuses to claim a cheapest facility when pricing/spread master data is missing.
- Cash-pool sweep outputs are `PROPOSED_NOT_EXECUTABLE` and stay within validated member contribution/funding capacities.
- Scenario search is a deterministic grid search. Breach counts are not converted into probabilities.
- Decision-pack resilience scores are transparent internal comparison scores. They are not accounting, regulatory or market-risk measures.
- GPT-6 Astra may compare and explain strategies but has `execution_authority = NONE`.

## MVP-12 enterprise liquidity command layer

MVP-12 adds a balance-sheet-style treasury view without turning the platform into an accounting ledger. It keeps contractual liquidity, contingent funding, interest-rate cash sensitivity and valuation sensitivity separate.

```text
Contractual cash flows + debt maturities
                ↓
Structural liquidity ladder
                ↓
Opening deployable cash ── committed facilities shown separately
                ↓
Survival / LaR / early-warning layer
                ↓
Contingency funding plan
                ↓
Funding tenor + cross-currency structuring
                ↓
Predictive balance-sheet treasury twin
                ↓
Specialist agents / Astra synthesis
                ↓
Human governance and existing execution controls
```

### Structural liquidity controls
- Probability-weighted receivables are contractual inflow estimates, not guaranteed cash.
- Debt principal maturities are contractual outflows.
- Undrawn facilities are contingent liquidity and are not added to contractual cash.
- Expiring facility capacity is displayed as a maturity risk rather than an inflow.

### Rate-risk controls
- Floating-rate cash sensitivity and DV01 are separate measures.
- The MVP-12 DV01 calculation is explicitly a transparent proxy where contractual reset schedules are unavailable.
- Production pricing/risk should use approved instrument schedules and curves.

### Funding optimization controls
- Tenor optimization targets refinancing resilience, not cheapest funding, unless executable all-in pricing is connected.
- Cross-currency structures cannot be economically ranked until local rates, FX forward/basis pricing, fees, tax and regulatory costs are validated.
- Intercompany facilities remain structuring mechanisms and do not create additional group liquidity.

### Contingency funding plan
Capacity is consumed sequentially to avoid double counting: transferable cash first, then committed external facilities, then escalation for new funding or asset-liquidity actions. The plan has no execution authority.

### Early-warning indicators
The EWI layer exposes directional green/amber/red thresholds without collapsing the treasury risk profile into an opaque AI score. Production thresholds require approval under the Treasury Risk Appetite Statement.

### Predictive balance-sheet twin
The balance-sheet twin is a treasury simulation. It combines operating liquidity, survival horizon, residual floating-rate cash exposure, FX economic sensitivity and collateral/derivative liquidity calls while preserving attribution. It is not an accounting forecast and cannot create or execute transactions.
