# Daily money summary

This beginner-friendly summary is a read-only view of the automatic simulator's supplied, validated synthetic snapshot. It does not fetch data, schedule updates, save records or execute payments or trades.

The component accepts `snapshot: DemoSnapshot | null` and `onNavigate`, restricted to `automatic` and `planning`. The dashboard supplies the snapshot. A missing or invalid snapshot yields an explicit unavailable result rather than fabricated balances.

The cash card uses existing engine-checked deployable USD cash, which subtracts restricted cash and commitments and excludes credit. Its current gap compares this figure with the configured minimum. Location warnings use the existing entity headroom and forecast shortfall; group cash does not authorize transfers.

The upcoming period includes the snapshot date and following six dates. Open flows are summed with fixed-point arithmetic within their native currency; no exchange rate or expected payment is invented. Overdue open records precede the snapshot date, show reference, entity and due date, and are excluded from upcoming totals. Open status is not evidence of nonpayment. Upcoming amounts are contractual scheduled amounts, not probability-weighted forecasts or guaranteed receipts.

The view prominently labels the simulated date, cycle and synthetic scope. It never presents the frozen fictional date as today's bank position. Failed market updates disclose retained rates. Real company daily monitoring still requires authenticated data, reconciliation, source timeliness and hosted infrastructure.
