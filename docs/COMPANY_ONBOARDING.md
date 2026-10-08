# Company treasury product foundation

This release adds industry-neutral company onboarding. It is a dedicated-company
product foundation, not an operationally certified universal SaaS service.
The public Vercel site allows session-only dummy profiles and entity drafts. It cannot save real company records. Drafts survive screen navigation; reload or Clear demo setup clears them. No server storage, role grants or engine activation occurs.

## Guided demo onboarding

Start blank or choose a fictional single-country or multinational oil-products
example. Examples are disabled while any profile/entity fields or saved draft are
present; Clear demo setup starts fresh. Country and currency fields offer common
code suggestions while allowing other codes for review. Suggestions are not
jurisdiction or currency certifications.

Your onboarding checklist counts the two metadata steps (saved profile and at least
one pending entity), then links to cash-flow testing, connections and readiness.
It does not claim bank connectivity, staff provisioning or production approval.
Download demo setup draft saves a JSON reference copy of the saved profile and
pending entities to the device. It excludes staff and engine entities, labels itself
fictional and unapproved, and cannot be imported or used as a cash-flow CSV.

## Customer deployment boundary

Provision separate frontend/backend deployments, PostgreSQL database credentials,
storage, identity application/audience, secrets and monitoring access for each
customer. Never point unrelated companies at the same database or identity audience.
The backend does not implement tenant filtering or shared multi-company hosting.
Infrastructure isolation must be verified by the operator, not inferred from a
profile name. Do not create a company switcher or accept client-selected tenant IDs.

Production bootstrap requires verified identity accounts and reviewed role
assignments. Company setup cannot create accounts or grant roles. Active company
users may read setup; only GROUP_TREASURER may save profiles or registrations.

## Onboarding workflow

1. Configure production hosting and company sign-in following PRODUCTION_DEPLOYMENT.md.
   Apply migration `0026_company_onboarding`. Production does not seed demo records.
2. Save the company profile: name, industry and two-letter country code. Profiles
   use an expected version to reject conflicting edits and create an audit record.
3. Register legal entities for review: legal name, country and functional currency.
   These are separate pending registrations, not engine-authoritative LegalEntity
   rows. Registration never modifies balances, FX, policy buffers or source authority.
4. The operator and accountable reviewers must verify legal identity, currency/FX
   support and engine entity configuration through the existing controlled process.
   Automated promotion of pending registrations is not implemented in this release.
   Country/currency fields validate code format only, not legal or market eligibility.
5. Configure bank/ERP/market mappings and ingest through governed connector interfaces.
   Retain SHADOW until certification, quality, parallel-run and human promotion pass.
6. Complete independent validation, security, resilience, UAT and release sign-offs.
   Missing bank, ERP, market, tax, legal and external evidence remains blocking.

Deployment `GROUP_REPORTING_CURRENCY` controls engine reporting currency. The
profile cannot change it. Currency changes require an operator-led configuration
and regression review. Industry metadata does not certify industry-specific models.

## Interfaces and controls

- GET `/api/v1/company/setup`: profile, pending registrations, configured engine
  entities, active staff display names/roles and deployment reporting currency.
- POST `/api/v1/company/profile`: strict schema, GROUP_TREASURER, singleton profile,
  optimistic version conflict handling and transactional audit record.
- POST `/api/v1/company/entities`: strict schema, company profile prerequisite,
  duplicate-name protection, pending-only registration and transactional audit.
- Next `/api/company?action=setup|profile|entities`: fixed paths, authenticated
  forwarding, same-origin JSON writes, 64 KiB body limit; recorded demo rejects writes.

The five GPT-6 Astra reasoning teams, token-efficient routing, deterministic engines
and human execution boundaries are unchanged. Mint explains the new workflow using
built-in guidance; live AI remains dependent on configured provider access.

## Remaining product and deployment work

Shared multi-tenant hosting, self-service account provisioning, reviewed entity
promotion UI, customer-specific connectors, independent security/restore tests and
external certification remain outside this implementation. A company profile is
not a certification, a production release sign-off or proof of infrastructure isolation.
