# MVP-8 Release Notes — Live Treasury Operations Layer

MVP-8 turns the institutional treasury-risk platform into an event-driven operating architecture while preserving the rule that AI and monitoring cannot move money.

## Added

- Immutable treasury event ledger with SHA-256 payload evidence
- Idempotent event ingestion and key-collision detection
- Sequence checkpoints, watermarks and event-lag monitoring
- Out-of-order and schema/type quarantine controls
- Bank-balance, FX-quote, ERP cash-flow, payment-status, heartbeat and execution-ack projections
- Deterministic continuous treasury monitor
- Live alert acknowledgement/resolution workflow
- Post-release execution-message envelope with payload hash/signature boundary
- Separate queued, sent, acknowledged and rejected execution states
- External connector identity boundary
- Event/execution Prometheus counters
- Four additional specialist agents
- Alembic migration `0008_live_ops`
- Command-centre live operations view

## Control boundary

`RELEASED_FOR_EXECUTION` means internal authorization is complete. It does **not** mean the bank executed the instruction. MVP-8 requires a separate execution message and external acknowledgement state. The demo does not make a real network call or move funds.

## Verification

- 58/58 backend tests passing
- Python compilation passing
- Frontend TypeScript source checked with local declaration stubs because frontend npm dependencies are not installed in this runtime
