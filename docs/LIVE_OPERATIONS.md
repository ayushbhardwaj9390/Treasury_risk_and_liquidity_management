# Live Treasury Operations Architecture

## Event flow

```text
Bank / ERP / Market / Payment Hub
              ↓
      Connector identity
              ↓
 Idempotency + schema + sequence gate
              ↓
     Immutable event ledger
              ↓
     Governed projection engine
              ↓
 Treasury current-state / risk engines
              ↓
 Continuous deterministic monitor
              ↓
 Alerts + specialist agents + Astra synthesis
```

The event ledger is evidence. Current-state tables are projections and may be rebuilt from authoritative history in a production implementation.

## Supported event types

- `BANK_BALANCE`
- `MARKET_FX_QUOTE`
- `ERP_CASH_FLOW`
- `PAYMENT_STATUS`
- `CONNECTOR_HEARTBEAT`
- `EXECUTION_ACK`

Schema version `1.0` is currently supported. Incompatible events are quarantined rather than applied.

## Idempotency and ordering

Each event carries an `idempotency_key`. Replaying the exact same event is safe and does not duplicate financial state. Reusing the same key for different content is treated as a collision. Sequence numbers protect connector order; stale sequences are quarantined.

## Execution lifecycle

```text
Approved proposal
      ↓
RELEASED_FOR_EXECUTION
      ↓
Signed/hash-controlled message envelope
      ↓
QUEUED
      ↓
SENT to external connector boundary
      ↓
ACKNOWLEDGED or REJECTED by provider event
```

`SENT` is not settlement confirmation. Provider-specific acknowledgements, settlement confirmations and reconciliation remain separate evidence.

## Autonomous monitoring boundary

The monitor can:
- detect liquidity/headroom risks
- evaluate LaR tail risk
- detect intraday funding need
- flag stale connectors and event exceptions
- create/refresh alerts

It cannot:
- create a treasury transaction
- approve a transaction
- release a transaction
- send a bank instruction
- alter treasury policy

## Production requirements

- workload identity or mTLS/JWT for connectors
- HSM/KMS-managed signing keys
- provider schema registry and compatibility policy
- durable event bus and outbox/inbox delivery pattern
- distributed checkpoint/circuit-breaker state
- encrypted immutable log retention
- provider-specific acknowledgement and settlement mapping
- operational runbooks and replay controls
