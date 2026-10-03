# Forecast Accuracy & Working-Capital Liquidity Intelligence

## Purpose
MVP-14 measures whether treasury cash forecasts have historically been reliable and links working-capital behavior to liquidity risk without turning operating assumptions into autonomous actions.

## Forecast performance
`forecast_performance_records` stores realized forecast/actual pairs with entity, flow type, counterparty, currency, horizon and model lineage.

Primary measures:
- **WAPE** = sum absolute forecast error / sum absolute actual cash flow.
- **Cash bias** uses liquidity direction. Over-forecast inflows and under-forecast outflows both create positive, optimistic cash bias.
- Horizon views: 0-7D, 8-30D, 31-90D and >90D.

Forecast history is immutable operational evidence in the target production design. Reforecasting must create a new version rather than overwrite prior forecasts.

## Working-capital cycle
`working_capital_observations` stores monthly revenue, COGS, receivables, payables and inventory by legal entity.

The engine calculates:
- DSO = AR / monthly revenue × 30
- DPO = AP / monthly COGS × 30
- DIO = Inventory / monthly COGS × 30
- CCC = DSO + DIO - DPO

Production implementations must align source accounts and period definitions to the approved corporate accounting policy.

## Receivables aging
Open AR is bucketed into CURRENT, 1-30, 31-60, 61-90 and 90+ days overdue. Treasury collection probabilities support timing forecasts only and must not be reused as IFRS/GAAP impairment estimates without an independently governed credit-loss model.

## Liquidity bridge
The bridge estimates illustrative cash release from DSO reduction, DPO extension and inventory-day reduction. It does not change commercial terms and has `execution_authority = NONE`.

## AI boundary
GPT-6 Astra may explain forecast bias, collection concentration and working-capital scenarios only from validated deterministic outputs. It cannot alter historical actuals, change forecast accuracy metrics, approve customer/supplier term changes or execute transactions.
