# MVP-14 Release Notes — Forecast Accuracy & Working-Capital Liquidity Intelligence

## Scope
MVP-14 strengthens the liquidity-risk platform by measuring whether cash forecasts have historically been reliable and by linking working-capital behavior to liquidity headroom.

## New deterministic engines
- Forecast Accuracy & Bias Engine
- Working Capital Cycle Engine
- Receivables Aging & Collection Risk Engine
- Working Capital Liquidity Bridge Engine

## New governed data
- `forecast_performance_records`: realized forecast-vs-actual history with entity, flow type, horizon and counterparty lineage.
- `working_capital_observations`: monthly revenue, COGS, AR, AP and inventory observations used for DSO/DPO/DIO/CCC.
- Alembic revision: `0014_forecast_working_capital`.

## New agents
- Forecast Accuracy & Bias Agent
- Working Capital Cycle Agent
- Receivables Collection Risk Agent
- Working Capital Liquidity Agent

The runtime now registers **72 specialist agents**. New agents are on-demand to preserve dashboard latency and GPT-6 Astra token efficiency.

## Key controls
- Positive cash bias always means historical liquidity forecasts were optimistic.
- WAPE is used instead of MAPE for aggregate cash-flow accuracy to avoid instability from small actual values.
- Collection probability is a treasury timing input, not an impairment/ECL estimate.
- DSO/DPO/DIO use governed working-capital observations and are not inferred from arbitrary open-invoice snapshots.
- Working-capital cash release is scenario analysis only and retains `execution_authority = NONE`.
- Customer terms, supplier terms and inventory policy remain human-owned operating decisions.

## Verification
- 99/99 backend tests passed across clean-database regression blocks.
- 7 dedicated MVP-14 tests passed.
- Alembic upgraded cleanly through `0014_forecast_working_capital`.
- Python compilation passed.
- Frontend TypeScript source verification performed separately from the production Next.js dependency install.
