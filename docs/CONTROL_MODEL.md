# Treasury Control Model — MVP-5

## Demo role matrix

| Role | View | Create | Approve L1 | Approve L2 | Risk review | Release | Audit |
|---|---:|---:|---:|---:|---:|---:|---:|
| Treasury Analyst | ✓ | ✓ |  |  |  |  |  |
| Treasury Manager | ✓ | ✓ | ✓ |  |  |  |  |
| Group Treasurer | ✓ | ✓ | ✓ | ✓ |  |  |  |
| Risk Manager | ✓ |  |  |  | ✓ |  |  |
| Payment Operator | ✓ |  |  |  |  | ✓ |  |
| Auditor | ✓ |  |  |  |  |  | ✓ |

## Hard control examples

- proposer cannot approve own transaction
- approver cannot release the same transaction
- material transactions require two approvals and Group Treasurer participation
- stale primary FX data blocks FX hedge proposals
- failed reconciliation blocks transaction release
- hedge notional cannot exceed residual business exposure
- an FX derivative must map to an underlying exposure
- cash transfers cannot exceed transferable legal-entity surplus
- facility draws cannot exceed undrawn committed capacity
- intercompany lending cannot exceed approved facility capacity
- configured transfer-pricing range is a control
- unreviewed tax rule blocks cross-border funding execution
- controls are re-run immediately before release

## Important distinction

A `WARN` is visible but does not automatically stop execution. A `BLOCK` does. Production governance should define exception authorities and whether specific warning classes require documented override approval.

## MVP-6 controls

- ML forecasts cannot mutate accounting cash flows or payment records.
- Payment models require validation metrics and drift monitoring before reliance.
- Anomaly detection is a review signal, never proof of fraud.
- IPV exceptions are independent valuation-control items and cannot be overridden by Astra.
- Approved market-data fallback is explicit and auditable.
- Unresolved payment-screening matches block treasury execution pending compliance disposition.
- Integrated stress keeps FX economic value sensitivity separate from cash liquidity unless a validated cash-flow transmission mechanism exists.

## MVP-7 institutional controls

- **Legal netting:** close-out netting is recognized only where enforceability and legal opinion status are approved. Otherwise exposure remains gross.
- **Model governance:** challenger outperformance can trigger review but cannot auto-promote a production model.
- **Valuation:** pricing terms, curves and volatilities are governed inputs; model value, book MTM and IPV remain separate measures.
- **Liquidity-at-Risk:** probabilistic outputs are scenario distributions, not guaranteed maxima; tail risk cannot override deterministic buffers or limits.
- **Production identity:** development headers are rejected in production. OIDC/JWT verification is required before protected write actions.
- **Write replay protection:** production treasury write routes require an idempotency key.
- **Connector resilience:** adapters use retry/circuit-breaker boundaries and must retain source/provider identifiers for reconciliation.
- **Operational resilience:** Tier-1 services carry RTO/RPO, multi-region and DR-test evidence; gaps are surfaced to the treasury control layer.

## Live operations controls (MVP-8)

- Event idempotency is mandatory at the ledger boundary.
- An idempotency key cannot be reused for different payload content.
- Sequence rollback is quarantined.
- Older bank/market events cannot overwrite newer governed state.
- Unsupported schema or event types remain in the evidence ledger but are not projected.
- Connector identity is separate from treasury-user identity.
- Continuous monitoring is alert-only and has no transaction authority.
- Execution messages are created only after human release.
- Bank/provider acknowledgement is a separate status from internal release.
- Execution-message payload hash/signature evidence is persisted.
- Production signing keys must be externalized to HSM/KMS or an equivalent managed key service.
