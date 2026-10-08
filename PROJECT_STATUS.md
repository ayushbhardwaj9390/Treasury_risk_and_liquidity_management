# Global Treasury AI — Project Status: Production Phases 2–4

## Guided company onboarding and Excel clipboard input — 8 October 2026

Company setup now offers blank entry, fictional single-country/MNC quick starts,
country/currency code suggestions, a metadata checklist and a downloadable JSON
reference draft. Examples cannot replace existing entries; downloaded drafts contain
only saved dummy profile/pending entities and explicitly deny production approval.
Cash planning accepts a copied Excel table with headings through the existing TSV
mapping/validation workflow. Native XLSX file upload remains unsupported.

Local verification passed 72 frontend regressions, type checks and production build.
Browser checks passed both quick starts, overwrite prevention, reset, JSON export
contents and pasted two-row cash-flow validation/calculation (USD 1,500 ending cash).
No browser console errors were observed. No schema, engine, role or evidence-gate
changes are required. Real storage, identity and source certifications remain blocking.

## Editable dummy setup and blue/slate theme — 8 October 2026

Company setup now accepts fictional profile and entity drafts in the public demo.
Drafts stay only in browser memory, survive screen navigation and clear on reload
or Clear demo setup. They do not configure engines, grant staff roles, write to a
backend or clear production gates. Real saves still require company sign-in and
the appropriate backend role. Basic names/codes/industry validation and duplicate
entity checks protect the demo workflow. Rodger explains the distinction.

The interface now uses a consistent blue/slate palette across navigation, charts,
forms, notices and Rodger's guide. Local checks passed 71 frontend regressions,
type checks and production build; browser checks passed typing, profile saving,
US/German entity drafts, navigation retention, duplicate rejection and reset.

Code commit `8adc61f` passed full backend/frontend CI, including regressions,
compile/type/build checks, calculator comparisons, migrations and dependency audits:
https://github.com/ayushbhardwaj9390/Treasury_risk_and_liquidity_management/actions/runs/37736621824.
Published company setup passed desktop and 390px phone checks, draft retention,
reload clearing and Rodger guidance. The sample cash planner calculated a delayed
receipt comparison and enabled its download. No browser console errors appeared
during these checks. Real company storage, hosted identity and external production
evidence remain blocking; these checks do not establish certified production readiness.

## Mint comprehensive interface guide — 8 October 2026

Mint now separates Screen guide, Ask Mint and Full app tour. One instruction at a
time, per-screen questions, a 13-workspace guide selector and a 13-stop tour cover
company setup, planning, automatic updates, cash/risk/funding reports, connections,
release workflows, AI teams and analysis discovery. Follow-up context is scoped to
the current screen; curated examples, recovery and role guidance preserve boundaries.
All five release Task flows are explained without submitting or approving records.
Mint remains a curated instant guide with no live model calls or private-data access.

Local verification: 68 frontend regressions and production compile/type/build checks
passed. Browser checks passed all 13 guide selections and tour stops, instruction
navigation, questions, stale-context prevention, 390px layout and Escape focus return.
Code commit `23faf5c` passed full backend/frontend CI, including regressions, compile/type/build checks, calculator comparisons, migrations and dependency audits: https://github.com/ayushbhardwaj9390/Treasury_risk_and_liquidity_management/actions/runs/37733985201. Published guide/tour navigation, governance instructions and 390px mobile layout passed browser checks. See `docs/MINT_GUIDE.md`. Hosted identity and real production evidence remain blocked.

## Parallel agent review — 8 October 2026

Three agents independently reviewed calculations, interface usability and deployment/security.
The review added 52 independent entity-forecast comparisons across the 26 dummy snapshots,
fixed overlapping company-setup initial loading, expanded Mint's single-country/MNC guidance,
and applied security headers and request IDs to early backend rejection responses.
All 62 frontend regressions pass. Code commit `03e7d2b` passed full backend/frontend Linux CI, including six new middleware regressions, compile/type/build checks, 26 group snapshots, 52 entity forecasts, migrations and dependency audits: https://github.com/ayushbhardwaj9390/Treasury_risk_and_liquidity_management/actions/runs/37732791961. The live site passed updated Mint guidance and MNC mode checks at desktop and 390px mobile widths with no page-wide overflow. Local backend pytest stalled before results on Windows; Linux CI provides verification. External evidence and live execution boundaries remain unchanged.

## Automatic dummy treasury updates — 8 October 2026

Automatic updates now provides separate fictional single-country and multinational manufacturing-company feeds:
matched bank/ERP settlements, new invoices, delayed receipts and FX quotes refresh
cash, forecasts, hedge coverage and risk alerts together. Duplicate/colliding events
and invalid market quotes demonstrate rejection without contaminating positions.
Existing hedge notionals are never executed or changed. The workspace pauses when
hidden or left; it is not a hosted background scheduler. Other dashboard reports
remain recorded demonstrations. The MNC example separates three country entities, local currencies and buffers from USD group totals; cross-border transfers remain subject to independent approvals.

Local verification: 61 frontend tests, type checking and production build passed;
all 26 snapshots matched unchanged Python liquidity, forecast and hedge-coverage
engines in isolated in-memory databases. No migration is required; the schema head
remains `0026_company_onboarding`. Code commit `5c250c5` passed the complete backend and frontend CI, including regressions, compile/type checks, migrations, calculator parity and dependency audits: https://github.com/ayushbhardwaj9390/Treasury_risk_and_liquidity_management/actions/runs/37731607473. The published workspace passed desktop and 390px mobile checks, automatic progression, structure reset, rejection/recovery and last-snapshot retention during a deliberate local outage. See `docs/AUTOMATIC_DUMMY_UPDATES.md`.

Real company feeds, hosted workers and external production evidence remain blocking.
No confidential data, live AI call, provider certification or go-live approval is claimed.

## Company product foundation — 6 October 2026

Industry-neutral company setup now includes a persisted profile, pending legal-entity
registrations, staff-role visibility and guided links to cash planning, connections
and release readiness. The Group Treasurer can save setup metadata with an audit
trail; profile versions reject conflicting saves. Pending entities remain separate
from engine-authoritative entities. No balances, approved policies or source
authority are changed by setup.

Migration head is `0026_company_onboarding`. The frontend production build and
51 frontend tests passed locally. Clean SQLite upgrade, schema comparison and
downgrade/re-upgrade passed for the onboarding tables; PostgreSQL deployment
verification remains outstanding. See `docs/COMPANY_ONBOARDING.md`.

Commit `9fe0988` passed the complete GitHub backend and frontend CI, including all
regressions, compile/type checks, calculator parity, migrations and dependency
audits: https://github.com/ayushbhardwaj9390/Treasury_risk_and_liquidity_management/actions/runs/37452893761.
Local backend pytest runs were interrupted after a Windows WMI/system-information
failure or stall; the unmodified Linux CI suite provides the backend verification.
The published company setup screen passed navigation and disabled-demo-write checks
at 1280px and 390px browser widths, with no page-wide horizontal overflow observed.
Real identity-provider login and company persistence on hosted infrastructure remain
unverified because no hosted company backend/identity configuration was provided.

Customer deployments must have separate databases, identity configuration and
secrets. Shared multi-company tenant isolation and automated promotion of pending
entities are not implemented. The public demo cannot save company records. Hosted
customer infrastructure, real feeds and external production evidence remain blocking.

## Current release — 3 October 2026

The synthetic energy pilot has now executed five scenarios through the unchanged
liquidity/forecast engines, with independent cash-arithmetic checks passing.
Delayed receipts and increased costs expose interim buffer shortfalls; the
combined case reaches USD 6.71 million. Incomplete-release execution was denied.
See `pilot/ENERGY_PILOT_REPORT.md`. Real enterprise testing remains outstanding.

Enterprise pilot preparation now includes `pilot/START_HERE.md`, an unassigned
scope worksheet, all 17 blocking evidence gates with required roles, and 19 UAT
starting scenarios. No enterprise credentials, actual approvers or deployment
environment have been provided; no real-provider tests or live activation occurred.

Revision 2 closes five regression cases around per-metric freshness, unmatched
payments, rollback after halt, and execution decisions using refreshed locked
release state. The deployment status remains blocked by external evidence.

The code-side validation candidate adds independent model benchmarking, model/version
coverage gates, production security hardening, release-scoped UAT and parallel-run
evidence, role sign-offs, controlled go-live/halt/rollback, execution gating and
production monitoring. Its original migration head was `0025_production_governance`;
the company setup addition advances it to `0026_company_onboarding`.

**Production status: BLOCKED pending real external evidence and human approvals.**
No provider, tax/legal, model, security, UAT or executive certification is claimed.
The five senior GPT-6 Astra teams, deterministic engines and human execution
boundaries are preserved. See `docs/PRODUCTION_PHASES_2_4.md` for controls and
runbooks, and `PRODUCTION_PHASES_2_4_TEST_EVIDENCE.md` for measured verification.

Earlier Phase 1 history follows; its readiness percentages are historical estimates,
not certification or evidence of this release's deployment readiness.


## Connected workflow candidate — 6 October 2026

The public Vercel demonstration was deployed from main and its 77 recorded analysis endpoints passed checks. This release adds company authorization-code sign-in with PKCE, secure HttpOnly cookies, verified active-account identity, and browser forms for release candidates, evidence fingerprints, parallel comparisons, sign-offs and release decisions. Demo writes remain denied. Registered connector ingestion now supports a separate verified JWT workload audience bound to source type; no real provider connection is claimed. Backend role checks and independent approval rules remain authoritative.

Deployment preparation now requires explicit PostgreSQL credentials and identity configuration, runs migrations before the API container starts, and checks database readiness. No new external service or paid account has been provisioned. Hosted backend/database deployment, a real identity-provider login, real workload-issuer verification, real company feeds, paid model access, PostgreSQL restore/load drills and independent reviews remain outstanding. They are not represented as completed or certified.

See `docs/CONNECTED_WORKFLOWS.md` for configuration and outstanding verification. No live source was promoted and no release was activated.

## Private planning addition — 6 October 2026

The application now includes an **Upload & what if** workspace: CSV/TSV column mapping, whole-file validation, a preview/apply boundary, explicit cash/buffer/FX assumptions, fresh deterministic scenario comparisons and CSV exports. Files stay in browser memory. Real balances, governed forecasts, evidence and payments remain unchanged. Seven synthetic cases compare the local calculator with the unchanged Python forecast engine. Commit `982e761` is deployed publicly; its complete GitHub CI passed. Live valid-upload, simulation, stale-export blocking and downloaded CSV checks passed. Phone/tablet testing remains unverified because the browser viewport override did not apply. See `docs/PLANNING_SANDBOX.md` for usage, test evidence and limits. This feature does not clear any external production-readiness gate.

## Production Phase 1 progress

The build has entered **Real Data & Integration**. The platform now has governed ingress and reconciliation plumbing for external treasury data rather than relying only on synthetic seed data.

Completed:
- ISO 20022 cash reporting ingestion
- canonical bank / ERP / market contracts
- SAP S/4HANA and Oracle Fusion adapter boundaries
- external ID mappings
- lineage and payload fingerprints
- quarantine and idempotency collision controls
- detailed bank-to-ERP reconciliation
- real-data coverage metrics
- evidence-based connector certification
- connector identity / schema enforcement
- migration `0023_real_data_integration`
- migration `0024_parallel_validation`
- SHADOW/ACTIVE/BLOCKED source-authority controls
- parallel-run evidence and data-quality SLA gates
- governed source promotion and quarantine resolution

Current phase status: **INTEGRATION_UAT / PARALLEL_VALIDATION**. Real provider domains remain in SHADOW mode until connector certification, data-quality SLAs and representative parallel-run evidence pass. No connector or data domain is treated as production-authoritative merely because an adapter exists.

## Overall position

The planned MVP-1 through MVP-22 architecture is now implemented as a coherent treasury-risk platform.

Estimated completion against the **designed application scope**:
- Treasury and liquidity functional architecture: **~97%**
- Risk/derivatives/model-control architecture: **~95%**
- Enterprise pilot readiness with controlled/synthetic data: **~90%**
- Live-MNC production readiness: **~60%**, because external systems, production data, security certification and jurisdiction-specific approvals are environment-dependent and cannot be fabricated.

These percentages are engineering estimates, not certifications.

## Completed through MVP-20

### MVP-15 — Legal-entity liquidity and cross-border constraints
- 90-day projected legal-entity liquidity deficits
- Transferable-surplus routing
- Legal/regulatory/tax route graph
- Approved-route caps and estimated withholding cost
- Blocked and unresolved funding needs stay visible
- Zero execution authority

### MVP-16 — Enterprise integration layer
- Bank / ERP / market / TMS / tax connector catalog
- Canonical connector contract
- Idempotency / reconciliation capability controls
- Freshness, latency and error-rate controls
- Retry and circuit breaker
- Event ledger / watermark / replay architecture

### MVP-17 — Security hardening
- OIDC/JWT production identity boundary
- RBAC and maker-checker
- Trusted hosts, configurable CORS and security headers
- HSM/KMS, secret-provider and SIEM interfaces
- Environment segregation controls
- Explicit security evidence status

### MVP-18 — Independent model governance
- Model registry and validation records
- Backtest / benchmark / stability design
- Champion-challenger governance
- Drift monitoring
- IPV and valuation-control framework
- No automatic model promotion

### MVP-19 — Role-specific operating model
- CFO workspace
- Group Treasurer workspace
- Risk workspace
- Treasury Operations workspace
- Tax workspace
- Audit workspace
- Investigation queues and ownership

### MVP-20 — Deployment and production gate
- PostgreSQL-ready persistence
- Alembic migrations through `0020_production_readiness`
- Docker references
- Kubernetes health probes
- CI pipeline
- Metrics and readiness endpoints
- Load-test harness
- Explicit GO / NO_GO deployment gate
- Human release-board authority


### MVP-21 — Predictive Treasury Risk Radar
- Dynamic market-regime classification from approved history
- Governed deterioration score, distinct from probability models
- Dynamic downside and combined stress scenarios
- Treasury-driver attribution across liquidity, survival, funding, market regime and forecast bias
- No execution authority

### MVP-22 — Strategic Treasury Optimization
- Treasury liquidity-buffer planning range
- Multi-year funding / fixed-floating / FX hedge / concentration strategy alternatives
- Explicit missing-executable-pricing control
- Human approval boundary preserved
- Five-agent Astra architecture retained with deterministic engines underneath

## Five-agent architecture

Astra calls are now consolidated into five top-level teams rather than calling every specialist individually:
1. Liquidity & Funding
2. Market & Derivatives Risk
3. Global Treasury & Tax
4. Risk, Controls & Model Governance
5. Treasury Orchestrator & Decision

All underlying specialist calculations remain intact. This reduces token use and latency without reducing treasury/risk coverage.

## What still requires a real MNC environment

1. Real bank/SWIFT connectivity and bank certification.
2. Real ERP/TMS integrations and end-to-end reconciliation UAT.
3. Licensed market-data feeds and production entitlements.
4. Actual company cash history, customer payment history, facilities, covenants, derivative confirmations and CSA terms.
5. Country-by-country tax, exchange-control and legal validation.
6. Independent model validation using company data.
7. HSM/KMS configuration and enterprise secret manager.
8. SIEM/SOC integration and penetration testing.
9. Production PostgreSQL HA cluster and backup/restore evidence.
10. Full DR/failover exercise and measured RTO/RPO.
11. Load/soak testing against the target infrastructure.
12. Treasury-professional UAT and final governance sign-off.

## Current production gate

The reference environment deliberately returns **NO_GO**. This is correct behavior: missing external evidence is treated as a blocker rather than silently assumed to exist.

## Mint application guide — 6 October 2026

Mint is an animated application mascot with contextual guidance for all ten workspaces, a six-step tour that opens the relevant screens, and bounded help answers for upload, simulation, privacy, cash buffers and go-live. It runs in browser memory, uses no external AI calls, and is explicitly labelled built-in help with no live AI connection. It does not read uploaded cash-flow contents, execute calculations or change evidence, approvals or payments. Keyboard close/focus handling and reduced-motion styles are included. This is a guide inside the treasury application, not a ChatGPT Work pet or an additional reasoning agent.

Verification: 39 frontend tests, TypeScript checks and the production build passed. Live checks completed all six tour steps, contextual help, an upload question and workspace navigation. No backend model, database schema, source authority or human-approval change was required.

## Mint contextual conversations — 6 October 2026

Mint now keeps up to 12 help exchanges in client memory, preserves conversations across workspace navigation, supports topic-aware examples and detail follow-ups, offers suggested questions and lets users clear the conversation. Whole-word/phrase matching replaces broad substring routing; specific validation questions take priority over generic upload questions. Ten help topics cover uploads, validation, assumptions, simulations, buffers, privacy, exports, governance, integrations and AI teams. Current-screen answers use the selected workspace; source-data questions distinguish recorded demo mode from a configured backend while preserving source-authority caveats. Unknown questions request a more specific app topic rather than inventing answers.

No live model credentials or provider connection were supplied. This remains explicitly labelled built-in guidance, separate from the five reasoning teams. Questions and file contents are not sent to an AI provider, uploaded files are not inspected by Mint, and approval/execution boundaries remain unchanged. All 47 frontend tests passed, including follow-up memory, routing collisions, validation priority, data-mode distinction and action boundaries.

## Task-first interface — 6 October 2026

The default Start here screen offers Explore the demo, Plan my cash flows and Review production readiness. The main navigation uses Dashboard, Cash planning, Risks, Data connections and Approvals & readiness; all specialist workspaces remain under More reports. Cash planning now has five stages: choose data, check records, set assumptions, try a scenario and read results. A fictional sample can be chosen explicitly; files still require whole-file validation and preview/application before assumptions. Continuing from assumptions uses the existing deterministic validation before allowing scenario entry. Results explain a buffer breach in plain language above the detailed metrics and weekly table. Dataset labels distinguish fictional versus uploaded data. Planning session state persists across workspace navigation; uploads, results and human approval boundaries are unchanged. Mint's tour and help wording follow the new entry point and cash-planning name.

Measured checks: 47 frontend tests, TypeScript checks and optimized production build passed. Live checks confirmed the new default entry page, explicit sample choice, required-assumption validation, a 10-day sample delay with USD 2.8 million week-2 shortfall, rejected duplicate CSV and valid uploaded-file application with cleared opening cash/buffer. Applying a replacement dataset also resets progress so old results cannot be opened as an empty step. No treasury-engine or migration change was required.

The public deployment was reported Ready by Vercel and the new Start here page was observed. Browser control later timed out while checking the remaining home shortcuts; those final shortcut checks and further device testing were not completed. The live guided-planning checks above were completed before that interruption.
