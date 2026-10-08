# Saved cash planning

The connected application can store one cash-planning draft in its dedicated company database. It contains checked cash-flow rows and the user's assumptions, not calculated engine records. It never activates a source, imports authoritative cash flows, or submits a payment or trade.

An authenticated active company user can read it. The `GROUP_TREASURER` role can save it. The existing OIDC identity boundary applies in production; accounts must be provisioned by the deployment administrator. This is not shared multi-company account creation. The public recorded demo has no hosted identity/database and cannot promise server persistence.

Run migration `0027_planning_drafts` after `0026_company_onboarding`. Register `app.api.planning_drafts.router` in the application and import `PlanningDraft` from `app.models.planning_drafts` in the models aggregator for Alembic metadata.

## Contract

`GET /api/v1/company/planning-draft` returns `{ "can_edit": true, "draft": null }` before the first save. After a save, `draft` contains `flows`, `assumptions`, `version`, `updated_at` (UTC) and `updated_by`.

`PUT /api/v1/company/planning-draft` accepts:

```json
{
  "expected_version": 0,
  "flows": [{"id":"receipt-1","entity":"Fictional company","date":"2026-10-12","direction":"INFLOW","currency":"USD","amount":"1500.00","category":"OTHER","probability":"1"}],
  "assumptions": {"start":"2026-10-12","weeks":2,"opening":"1000","buffer":"800","rates":{},"delay":0,"receipts":0,"costs":0,"oil":0,"fx":0}
}
```

The first save uses expected version 0. Subsequent saves use the last retrieved version. A stale or concurrent create returns 409; reload and review before retrying. Successful writes increment the version and create an audit event containing record count/version, without copying sensitive row contents into the audit log. The entire save commits atomically.

Validation rejects extra policy fields, duplicate references, invalid dates, unsupported currencies, missing non-USD rates, invalid amounts/probabilities and scenarios outside the existing planner bounds. Drafts contain 1–500 rows and a maximum serialized 512 KB. There is no automatic background save: the user chooses what to store. Deployment security, encryption, backup/restore and retention must be verified before real company data is hosted.
