# MVP-11 Release Notes

## Institutional Counterparty, Funding & Survival-Risk Layer

MVP-11 deepens the treasury-risk platform without expanding execution authority.

### Added
- Governed historical FX return observations and lineage
- EWMA volatility and dynamic correlation calibration
- Historical residual FX VaR, Expected Shortfall and 90-day EaR
- CVA/FVA-style counterparty sensitivities after legal netting and collateral
- 26-week liquidity survival horizon
- Funding-provider concentration, top-lender share and HHI
- Treasury risk-limit framework with deterministic warning/breach states
- 54-configuration digital-twin resilience search
- Six specialist agents, bringing the runtime to 56 agents
- Alembic `0011_institutional_depth` migration

### Control principles
- XVA outputs are risk sensitivities, not accounting fair-value adjustments.
- Historical calibration requires approved market-history lineage.
- Risk-limit breaches require human exception governance.
- Digital-twin optimization has `execution_authority = NONE`.
- Deterministic engines remain the source of financial values; Astra interprets validated outputs only.
