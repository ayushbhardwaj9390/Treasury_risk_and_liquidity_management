# Warning explanations

`WarningReview({snapshot: DemoSnapshot | null})` can be mounted alongside the automatic dummy feed. `explainWarnings(snapshot)` returns structured deterministic explanations, or `null` when a snapshot is unavailable. There is no AI call, database write, trade or payment.

Each warning exposes its cause, supporting references, supplied dates/currencies, and a safe human review step. Cash checks exclude credit. Forecast evidence includes opening balances and open invoices through the first affected week; it is not single-invoice causal attribution. Currency checks expose the existing hedge and open invoices, including invoices beyond the forecast horizon. Remaining exposure is not a loss estimate. Missing contract maturities and quote timestamps are explicitly unavailable. Entity warnings prohibit assuming consolidated cash is transferable. Rejected records remain visible after recovery and do not imply the underlying transaction never occurred.

Scope: fixed fictional feed only. Real-company explanations require validated source records, permissions and approved integration. This feature grants no approval or source authority.
