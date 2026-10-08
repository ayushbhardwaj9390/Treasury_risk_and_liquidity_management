# Automatic treasury updates with dummy data

The Automatic updates workspace processes a fixed fictional manufacturing-company
feed for either a single-country US business or a multinational group with US, German and UK entities. Each country has a functional currency and cash buffer; group totals report in USD. Group cash does not authorize pooling or cross-border transfers. No confidential data, credentials or uploads are requested or accepted by its
endpoint. It is separate from company records and the recorded dashboard.

## How to use it

Open Automatic updates choose the operating structure and select Start automatic updates. One event is processed
every five seconds after the preceding request completes. Pause, process one event
manually or restart the example. The 12-event feed stops at completion; it never
loops balances indefinitely. Leaving the workspace or hiding the tab pauses it.
The last snapshot stays in browser memory when switching screens; reload clears it.
This is a visible-workspace simulation, not a persistent background scheduler.

Events represent matched customer/supplier settlements, new ERP invoices, invoice
due-date changes and EUR/GBP market quotes. They include a duplicate, a conflicting
reference and a bad market quote for rejection checks. Values are invented, not
Shell data or market prices. The planning date is fixed at 8 October 2026; the
calculation timestamp records the actual response time, not real-source freshness.

## Recalculation and boundaries

- Cash: currency-converted bank balances less restricted cash and commitments;
  no credit facilities assumed. Headroom is available cash less the dummy buffer.
- Forecast: fresh 13-week calculation with existing fixed-point planner arithmetic.
  Matched settlements remove their open invoice, avoiding double counting.
- FX: open receivables less payables; existing BUY/SELL hedge notionals remain fixed.
  Coverage uses the existing engine's 60â€“90% default range. Direction mismatches
  get an additional review alert. Open flows beyond the forecast horizon remain
  in currency exposure. USD is excluded from foreign-currency hedge coverage.
- Risk: buffer shortfalls, hedge coverage/direction and absolute residual FX exposure.
  Residual exposure is not VaR, predicted loss or a derivative valuation. Interest,
  commodity, counterparty and other specialist reports are not refreshed by this feed.

The server computes the complete event prefix and replaces all position cards with
one coherent response. Repeated requests for the same cycle are deterministic and
cannot accumulate postings. Duplicate deliveries are ignored; mismatched references,
unsupported messages, invalid quotes and out-of-order changes are quarantined. A
bad quote never replaces valid rates; conversions are labelled last validated until
a good refresh arrives. Network errors pause updates and preserve the last successful
snapshot. Users can retry that same next cycle. Pause/reset abort pending requests;
generation checks prevent late responses from overwriting the selected position.

GET `/api/automatic-demo?cycle=0..12&scope=single|mnc` accepts only a bounded cycle and one of two fixed fictional structures. Other query keys,
duplicate parameters and unsupported methods are rejected. It has no company-data
input and performs no database, connector, model, payment or trading writes.
Responses carry no-store and explicit SYNTHETIC_AUTOMATION provenance. Its event
history is session demonstration evidence, not a production audit ledger.

Five GPT-6 Astra teams, token-efficient routing, source-authority policies and human
approval boundaries are unchanged. No model tokens are used on automatic refreshes.
Real sources are not promoted and external readiness gates stay blocked.

## Verification

All 26 snapshots (13 per structure) are independently compared with the unchanged Python global
liquidity (including entity-local cash and group conversion), group 13-week forecast and hedge-coverage engines in disposable in-memory DBs.
`scripts/export_automatic_demo.cjs` exports the TS contract fixture;
`scripts/verify_automatic_parity.py` checks Python parity; frontend tests compare
runtime output with the verified fixture and exercise duplicate/collision/validation
and reconciliation boundaries. CI runs both full regression suites, migration checks,
compile/type checks, production build, parity and dependency audits.

## What remains before real automation

This does not implement production bank/ERP/market subscriptions or a hosted worker.
Real automation needs customer-specific hosting/identity, verified connector data,
durable queues/checkpoints, scoped idempotency, source quality and stale-data gates,
reconciliation, monitoring/recovery evidence and the existing independent release
sign-offs. Uploading a private CSV alone cannot create these connections. Trade,
hedge, payment and source activation decisions remain human-controlled. No external
certification or provider access is fabricated.

## Published release verification — 8 October 2026

Code commit `5c250c5` is published on the authorized GitHub main branch and Vercel site.
Complete CI passed: https://github.com/ayushbhardwaj9390/Treasury_risk_and_liquidity_management/actions/runs/37731607473.
Local checks passed 61 frontend tests, type checks, build and 26 independent engine comparisons.
Browser checks verified both structures, automatic progression, pause, screen switching,
completion, invalid-quote rejection/recovery, and structure changes resetting to cycle zero.
A deliberate local service outage preserved the previous position; retry after restoration
advanced exactly once. The published MNC mode was checked at 1280px and 390px,
with no page-wide overflow at 390px. Real hosted identity and external connections
remain unverified and blocked. No schema changes were needed in this release.

A subsequent three-agent review added independent maximum-shortfall and first-breach
checks for 52 entity forecasts in isolated databases, using source balances and
entity assumptions rather than expected TS totals. All comparisons passed; deliberate
incorrect shortfall and breach values were rejected. Mint now explains operating
structure and local-versus-group cash, and setup reload waits for initial loading.
