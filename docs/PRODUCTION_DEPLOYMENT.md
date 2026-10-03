# Production deployment boundary

MVP-8 is a reference enterprise architecture, not a turnkey production treasury system.

## Required production substitutions

1. Set `ENVIRONMENT=production` and use PostgreSQL or an approved enterprise database service.
2. Set `AUTH_MODE=oidc_jwt` and configure issuer, audience and JWKS URL. The development identity header is rejected in production.
3. Run schema changes through Alembic. `create_all` and synthetic seeding are development-only behavior.
4. Store API keys, DB credentials and signing material in a managed secrets service. Never commit them.
5. Implement authenticated bank, ERP, market-data and screening connectors behind the supplied contracts and resilient runner.
6. Require idempotency keys for treasury write requests and preserve provider acknowledgements for reconciliation.
7. Validate pricing models, curves, volatility sources, LaR/CFaR methodology and model thresholds independently before production use.
8. Obtain current legal opinions for close-out netting and approved CSA/collateral master data.
9. Complete penetration testing, threat modelling, DR tests, incident runbooks and operating procedures.

## PostgreSQL / Alembic

Development can run directly with SQLite. For production, configure `DATABASE_URL` with a PostgreSQL URL and run Alembic from `backend/`.

For a fresh repository database, `0006_predictive` bootstraps the current schema and `0007_institutional` is idempotent over that bootstrap. For an existing MVP-6 database, stamp the database at `0006_predictive` only after confirming its schema matches the prior release, then apply `0007_institutional`.

Never stamp an unknown production schema without a reviewed migration plan and backup.

## MVP-8 eventing and connector deployment

The demo persists its event ledger in the application database. Production should place an enterprise event bus or durable queue in front of ingestion, use an inbox/outbox pattern, and retain immutable evidence according to the organization's treasury, audit and regulatory retention rules.

Connector authentication must not use the demo `X-Connector-Name` header. Use workload identity, mTLS and/or signed service JWTs with connector-specific audiences and least-privilege claims.

Execution signing secrets must not be plain environment strings in a mature deployment. Use HSM/KMS-backed signing and key rotation. Provider acknowledgements and settlement confirmations must be mapped separately and reconciled to the original message and internal transaction proposal.
