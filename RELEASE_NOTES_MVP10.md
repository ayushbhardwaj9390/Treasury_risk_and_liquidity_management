# Global Treasury AI — MVP-10 Release Notes

## Treasury Digital Twin & Enterprise Risk Intelligence

MVP-10 adds a forward-looking digital-twin layer on top of the existing deterministic treasury, live-operations, controls and optimization stack.

### New engines
- Treasury Digital Twin
- Residual FX VaR / Expected Shortfall / 90-day Earnings-at-Risk
- Liquidity Transfer Pricing
- Bank Account Rationalization

### New specialist agents
- Treasury Digital Twin Agent
- Market VaR & EaR Agent
- Liquidity Transfer Pricing Agent
- Bank Account Rationalization Agent
- Enterprise Treasury Risk Committee Agent

Total specialist agents: **50**.

### Control principles
- Digital-twin output is advisory only.
- VaR and EaR are modelled distributions, not worst-case guarantees.
- Missing approved FX volatility is surfaced and replaced only by an explicit policy proxy in the synthetic demo.
- Liquidity transfer pricing is management economics and is not legal/tax transfer-pricing advice.
- Bank-account closure is never automated.
- Existing maker-checker, policy, screening, legal-netting and execution boundaries remain unchanged.

### New APIs
- `GET /api/v1/digital-twin`
- `POST /api/v1/digital-twin/simulate`
- `GET /api/v1/risk/market-var`
- `GET /api/v1/liquidity/transfer-pricing`
- `GET /api/v1/operations/bank-account-rationalization`

### Verification
- 71/71 backend tests pass across clean split regression runs (63 non-MVP8 + 8 MVP8).
- Python compilation passed.
- Frontend TypeScript source check passed using local declaration stubs because the runtime does not contain the npm dependency tree.
