# Company preference drafts

The Company setup screen can describe a domestic or multinational business using supported countries, currencies, a suggested USD minimum cash target and suggested reviewer roles. The public demo retains fictional preferences only in component memory; reloading clears them. It does not send them to the server.

Connected deployments use authenticated `GET` / `PUT /api/v1/company-preferences`. Active company accounts can read; only `GROUP_TREASURER` can save. PUT requires `countries`, `currencies`, `minimum_cash_usd` (decimal string), `reviewer_roles`, and `expected_version`. The first version expects 0; subsequent updates must supply the returned version. Concurrent stale writes fail rather than overwriting. Every successful save records an audit event without recording the full payload. Migration `0028_company_preferences` follows `0027_planning_drafts`.

The singleton store belongs to one dedicated company deployment. It is not tenant isolation for unrelated customers. Hosting the database and company identity service remains an external prerequisite.

All records return `DRAFT_NOT_ACTIVATED`. Saving does not change authoritative entities, reporting currency, source authority, calculation inputs, transaction policies, approval requirements or user roles. Reviewer choices refer to existing role names; they grant no access and create no approval. Actual policy activation remains outside this draft workflow and requires the existing controlled review and evidence process.

Supported countries: US, GB, IN, DE, FR, SG, AE, HK, CN, JP, CH, CA, AU, NL, SA, BR, ZA. Supported currencies: USD, GBP, INR, EUR, SGD, AED, HKD, CNY, JPY, CHF, CAD, AUD. Other jurisdictions and currencies require reviewed support; selecting a country is not tax or legal certification. A group USD target is neither entity-level liquidity nor a statement that funds can move across borders.
