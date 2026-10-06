# Company onboarding release — 6 October 2026

The application now starts with company setup, private cash planning and readiness
review. Company onboarding supports manufacturing, services, retail, energy,
financial services and other industries as metadata; industry selection does not
certify models or compliance.

Implemented:

- Authenticated company profile persistence with singleton deployment boundary,
  version-conflict protection and audit records.
- Pending legal-entity registrations, duplicate protection and separate storage
  that cannot change deterministic treasury calculations or activate sources.
- Staff-role visibility, Group Treasurer write checks and fixed authenticated
  frontend proxy routes with origin, format and size validation.
- Responsive setup workflow and Mint guidance; energy examples remain under reports.
- Migration `0026_company_onboarding` and dedicated-customer deployment instructions.

Verification for application commit `9fe0988`:

- Complete backend/frontend GitHub CI passed, including regressions, compile/type
  checks, calculator parity, migrations, dependency audits and production build.
- 51 frontend tests passed locally. Clean SQLite upgrade, schema comparison and
  downgrade/re-upgrade passed locally.
- Published setup navigation and disabled demo forms checked at 1280px and 390px;
  document width remained within the viewport. These checks do not certify every
  device or all connected-company workflows.
- Windows local backend pytest was interrupted after WMI failure/stalling; Linux
  CI passed without any test-environment workaround.

CI evidence: https://github.com/ayushbhardwaj9390/Treasury_risk_and_liquidity_management/actions/runs/37452893761

Production remains BLOCKED_EXTERNAL_EVIDENCE. Each customer needs separately
configured hosting, database, identity and real connectors. Shared multi-company
tenant isolation, self-service access provisioning and automated pending-entity
promotion are not implemented. Hosted persistence/OIDC and PostgreSQL recovery
verification remain outstanding. No external certification or live AI is claimed.
