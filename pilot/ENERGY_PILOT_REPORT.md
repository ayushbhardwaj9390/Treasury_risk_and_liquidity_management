# Synthetic energy pilot results — 3 October 2026

The fictional Shell-inspired scenario was executed through the existing global
liquidity and 13-week cash forecast engines. Five isolated in-memory databases
were used; no real bank, ERP, payment or production database was contacted.

Opening cash is USD 34.8 million after converting GBP at 1.25 USD and SGD at
0.80 USD. These are assumed rates, not market observations. The minimum group
cash buffer is USD 15 million. Restricted cash, committed outflows and credit
facilities are zero; receipts have assumed probability 100%. Start date is fixed
at 3 October 2026. No additional flows beyond the sample dataset are assumed.

| Scenario | Lowest weekly closing cash (USD m) | First buffer breach week | Maximum buffer shortfall (USD m) | Ending cash (USD m) |
|---|---:|---|---:|---:|
| Base | 15.30 | None | 0 | 34.20 |
| Product receipt delayed 10 days | 12.20 | 2 | 2.80 | 34.20 |
| Crude purchase cost increased 20% | 11.70 | 1 | 3.30 | 30.60 |
| Non-USD operating cost uplift 10% | 15.30 | None | 0 | 33.89 |
| Combined stresses | 8.29 | 1 | 6.71 | 30.29 |

The cost uplift changes non-USD operating cashflows only. It is not a complete
FX revaluation of assets, liabilities or opening bank balances. Each stress is
applied to the sample cashflows, then the BASE forecast engine evaluates them;
the built-in MODERATE/SEVERE multipliers are not applied a second time.

Every weekly inflow, outflow, closing cash and headroom matched independent
Decimal cash arithmetic. Opening translated cash and the group buffer also
matched. All five calculations passed without missing-FX forecast warnings.
The new runner compiled successfully. Application engines were unchanged;
the prior complete 176-test regression result remains recorded separately.

An entity-level warning was retained: the Singapore entity opens with USD
4.8 million against its USD 5 million minimum, a USD 0.2 million deficit.
Positive group headroom does not prove cash is transferable to that entity.
Cross-border transfers require separate legal, tax and operational review.

An incomplete synthetic release remained BLOCKED with 31 blockers, and the
execution guard denied it. Its isolated test user and synthetic hashes are
test fixtures, not real approvers or deployment artifacts. No REAL evidence
or sign-off was supplied. Databases were disposed after the run.

The delay case demonstrates that eventual positive cash does not eliminate an
interim funding gap. The combined case exceeds the buffer by USD 6.71 million
at its worst weekly close. These are liquidity-buffer breaches, not negative
cash balances. No automated borrowing, payment or hedge was authorized.

Weekly aggregation does not prove daily or intraday solvency. This dataset is
small and excludes inventory valuation, commodity hedges, taxes, contractual
restrictions, realistic capacity and ongoing operations. It is not Shell's data,
independent certification, real UAT or a completed enterprise parallel run.

Reproduce with `.venv/Scripts/python.exe scripts/run_energy_pilot.py` from the
project root. Detailed values and input SHA-256 are in `ENERGY_PILOT_RESULTS.json`.
Real credentials, managed infrastructure, provider certification, 60-day real
comparisons, target-environment security/recovery checks and human approvals
remain mandatory before go-live.
