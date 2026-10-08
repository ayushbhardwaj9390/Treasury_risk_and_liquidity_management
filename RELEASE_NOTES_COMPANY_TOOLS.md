# Company tools release — 8 October 2026

## What users can try

Cash planning → Upload Excel / CSV imports values-only XLSX locally, lets users
choose a worksheet and map headings, and requires every record to pass checks.
Formula cells must be converted with Paste Special → Values. Limits: 2 MB XLSX,
10 MB expanded, 10 sheets, 500 data rows and 30 columns per sheet; CSV remains 512 KB.
Completed plans have a manual actual-versus-plan table using end-of-week USD cash.
Unknown values are excluded, zero is included, and percentage error has no value
when its denominator is zero. This does not train an AI.

Automatic updates shows a daily money summary and expandable explanations with
supporting fictional records. It continues to run only while its screen is open.
Its data is separate from uploaded planning files and recorded dashboard reports.
Company setup offers draft countries, currencies, minimum USD cash target and
suggested review roles. Public-demo edits remain in the browser session.
Data connections offers example scheduled-feed settings and visible missing data.
Rodger explains the new tools using built-in guidance without an AI network call.

## What requires deployment configuration

OIDC company sign-in and a dedicated hosted backend/database enable authenticated
planning-draft and preference persistence. Active accounts read; Group Treasurer
writes. Version conflicts prevent silent overwrites and saves are audited.
The company preferences remain metadata drafts; they do not grant access or activate
engine policies. Shared multi-tenant isolation is not implemented.

Scheduled requests are stored and compared with accepted connector checkpoint
freshness. The operator CLI records BLOCKED readiness attempts only: no approved
credential-backed collection adapter or deployed worker is bundled. It never stamps
successful collection, promotes SHADOW sources or executes financial actions.
Real connector certification, model validation, security/recovery evidence, UAT and
role-based release sign-offs remain separately blocking.

## Verification

Seven agents owned independent feature files; the primary integrated/reviewed them.
251 backend tests passed, clean migrations through 0029 and Alembic check passed.
Python compile and deterministic parity passed: 7 planning cases, 26 dummy cycles and
52 entity forecasts. 107 frontend tests, including proxy boundary tests, TypeScript and optimized
Next.js build passed. Production dependencies audited with no known vulnerabilities.
Browser tests imported both worksheets, verified USD 1,500 closing cash and USD 100
actual-versus-plan error, and saved clearly fictional preference/settings examples.
The complete dashboard/API smoke run passed all 80 checks.
No real external certification or confidential company data was used.

Details: docs/EXCEL_UPLOAD.md, docs/PLANNING_DRAFT_STORAGE.md,
docs/DAILY_MONEY_SUMMARY.md, docs/WARNING_REVIEW.md, docs/FORECAST_REVIEW.md,
docs/COMPANY_RULES.md and docs/SCHEDULED_UPDATES.md.
