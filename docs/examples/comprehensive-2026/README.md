# Fictional Harbor Energy test pack

All data is invented for testing. It is not Shell data, a bank statement, a market-data license, an external certification or a human approval.

## Upload the large Excel sample

1. Open Cash planning in the application.
2. Choose Upload Excel / CSV and select treasury-comprehensive.xlsx.
3. Select Cash flows 500. The eight columns should map automatically.
4. Choose Check data, then Use checked data.
5. Enter the settings below. Applying a file clears the previous assumptions, so enter these after applying it.
6. Run the plan. Compare it with expected-planning-results.json.

The workbook has 500 records, six fictional subsidiaries, 12 currencies and all five supported cash-flow categories. Amounts are full units of the currency on each row. Payments are positive numbers with OUTFLOW direction. Probability is a fraction, so 0.95 means a 95% chance of collecting the receipt. Excel displays it as 95%.

| Setting | Value |
| --- | --- |
| Start date | 2026-10-12 |
| Number of weeks | 13 |
| Opening cash in USD | 50000000 |
| Minimum cash reserve in USD | 30000000 |
| Receipt delay | 0 days |
| Receipt, cost, oil and currency changes | All 0% |

Enter these **assumed USD values for ONE unit** of each currency. They are fictional fixed rates, not live market quotes.

| Currency | USD per unit |
| --- | ---: |
| EUR | 1.17 |
| GBP | 1.34 |
| SGD | 0.775194 |
| INR | 0.010858 |
| JPY | 0.006711 |
| CHF | 1.12 |
| CAD | 0.74 |
| AUD | 0.66 |
| CNY | 0.14 |
| AED | 0.272294 |
| HKD | 0.128205 |

## What you should see

| Test | Settings changed from the base plan | Ending cash in USD | Largest reserve shortage in USD |
| --- | --- | ---: | ---: |
| Base | None | 70,079,900.11 | 0.00 |
| Customers pay late | Delay 21 days | 17,620,400.08 | 26,155,149.94 |
| Costs increase | Costs +25% | 19,069,425.11 | 12,919,124.88 |
| Collections fall | Receipts -25% | 14,049,450.08 | 15,950,549.92 |
| Oil price increases | Oil +20% | 89,680,160.12 | 0.00 |
| Currency change | Currency +15% | 74,649,102.63 | 0.00 |
| Combined adverse case | Delay 21 days, costs +25%, receipts -25%, oil +20%, currency +15% | -96,997,969.17 | 126,997,969.17 |

The base plan deliberately excludes four overdue records and four records beyond the 13-week horizon. With a 21-day receipt delay, 41 records move beyond the horizon. They are excluded from that plan, not deleted. Oil changes affect both crude purchases and product sales. Currency changes apply the same percentage to all non-USD cash flows. These are scenario assumptions, not commodity derivative valuations or individual currency forecasts.

The displayed opening cash is a manual planning assumption. It is not calculated from the backend's bank accounts. The reserve is a planning assumption and does not activate a company treasury policy. A weekly cash result can hide shortages during the week.

## The rest of the model

The public Cash planning upload imports **cash flows only**. It does not import the following tables or update the recorded dashboard snapshot. The full pack supplies a separate developer test database, table extracts, API request examples and test results for these components:

| Component | Supplied test data or evidence |
| --- | --- |
| Company setup and saved planning | Fictional profile, preference draft, 500-row saved planning draft; permission-denied test for an analyst editing the profile |
| Global cash and liquidity | Six legal entities, bank balances, cash restrictions, facilities, cash pools and intercompany funding |
| Forecasting and scenarios | 500 cash flows, scenario templates, seven upload scenarios and expected weekly balances |
| FX, hedging and derivatives | Forward, option and swap positions, hedge designations, valuation terms, curves and volatility quotes |
| Debt and interest-rate risk | Fixed/floating debt, credit facilities, maturities and covenant tests |
| Counterparty, collateral and netting | Limits, credit metrics, collateral agreements, netting sets and trade links |
| Market and liquidity risk | Historical returns, risk limits, stress inputs and simulation outputs |
| Working capital and forecast quality | Payment history, forecast performance and working-capital observations |
| Intraday cash and payment controls | Intraday payments, screening cases, anomaly inputs and transaction proposals |
| Cross-border and cash mobility | Restrictions, constraints and illustrative tax/legal rules; all require real professional validation |
| Data integration and source authority | Connector registrations, checkpoints, mapping and certification-control fixtures; real connections and certifications remain unavailable |
| Scheduled collection | Saved paused schedules; worker remains BLOCKED because approved adapters and credentials are absent |
| Five-agent architecture | Runtime and summary responses from the existing five treasury reasoning teams; no paid external model calls or fabricated AI certification |
| Model validation and resilience | Registry, validation, deployment and resilience fixtures; independent benchmark API example |
| UAT and release governance | 72 explicitly SYNTHETIC comparison observations across 12 days and six metrics; synthetic model evidence, a DRAFT candidate and a rejected GO_LIVE request |
| Production monitoring | Health/readiness responses, operational alerts and deployment-readiness fixtures; production health correctly returns 503 |

CSV table names and columns match the backend schema. Empty CSV tables contain headings only and identify workflows for which no records were created. In particular, no real sign-offs, approvals, execution messages, integration evidence or certifications are invented to fill empty tables. HTTP success means a component returned a response; its business readiness can still be blocked or require review.

The seed fixtures retain development bank labels and illustrative control statuses from the project's existing demo. Every record in this pack is fictional. A simulated PASS is not external evidence. Production gate and source-authority responses must be checked separately. No real transactions are executed.

## Files and developer use

- treasury-comprehensive.xlsx: upload-ready workbook.
- treasury-comprehensive.csv: equivalent upload-ready CSV.
- assumptions.json: settings for the upload tests; the interface does not import this JSON automatically.
- expected-planning-results.json: exact results, including all 13 weekly balances for seven scenarios.
- backend-tables/: schema-compatible CSV extracts for inspection; not files for the Cash planning uploader.
- backend-data.json: table counts, columns and explicit fictional-data classification.
- component-results.json: 80 dashboard and health checks with expected status codes.
- component-snapshots.json: responses produced by this larger backend test dataset. The public recorded dashboard is a separate dataset.
- backend-request-fixtures.json: synthetic examples for company drafts, schedules and release controls.
- workflow-evidence.json: actual test responses from the isolated draft/governance checks.
- fictional-test.db: the isolated SQLite development fixture. It contains no real company data or external credentials. Never point a production service at it.
- backend-check.py and workflow-check.py: reproduce the pack using the project's backend dependencies. Run backend-check.py with the repository path as its first argument in a fresh folder without fictional-test.db, then run workflow-check.py with the same repository path. The workflow runner resets only its draft/governance records in its dedicated fictional database before testing.

This data pack tests software behavior. Real bank/ERP connections, licenses, legal/tax opinions, independently signed validation, restore/load exercises and accountable release sign-offs require real evidence and remain blocking gates.
