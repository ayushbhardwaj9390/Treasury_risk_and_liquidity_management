# MVP-22 — Strategic Treasury Optimization

Adds multi-year treasury strategy and liquidity-buffer planning on top of the MVP-21 predictive layer.

## Added
- Optimal liquidity-buffer planning range using operating minimum, tail liquidity, intraday demand, collateral stress and refinancing reserve.
- Multi-year strategy alternatives for liquidity resilience, balanced treasury and risk stability.
- Fixed/floating debt targets, policy-constrained FX hedge targets, lender concentration targets and long-term funding targets.
- Explicit incomplete-pricing status until executable spreads, fees, FX basis, option premia, tax effects and ratings impacts are connected.
- New APIs:
  - `GET /api/v1/strategy/optimal-liquidity-buffer`
  - `POST /api/v1/strategy/treasury-plan`

## Controls
- Human approval required.
- Execution authority remains `NONE`.
- Strategic optimization does not forecast market direction or autonomously create transactions.
