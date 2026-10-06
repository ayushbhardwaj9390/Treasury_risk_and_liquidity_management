# Connected application workflows

## Delivered code

Company sign-in uses an authorization-code flow with PKCE and a signed, ten-minute state cookie. The backend verifies JWT access tokens against its issuer, API audience and signing keys, then requires an active treasury account. Roles are taken from the database; there is no browser role picker or automatic enrollment. Tokens are stored in Secure, HttpOnly, SameSite cookies and forwarded only on the server. Logout clears the application cookies; company-wide IdP logout and token refresh are not implemented. Expired tokens require sign-in again.

Configure the frontend using frontend/.env.example in the host's encrypted environment settings. Register APP_URL/api/auth/callback with the identity provider, enable S256 PKCE, and issue JWT access tokens for the backend OIDC_AUDIENCE. The flow supports client_secret_post or a public PKCE client; providers requiring a different client authentication method need an adapter. Configure backend ENVIRONMENT=production, AUTH_MODE=oidc_jwt, OIDC_ISSUER, OIDC_AUDIENCE, OIDC_JWKS_URL and the username claim. Create approved active UserAccount records whose usernames exactly match that claim using the organization's controlled account-provisioning procedure. Do not seed demonstration identities in production.

Release readiness now includes forms for candidate registration, evidence, comparisons, sign-offs and transitions. Evidence files are hashed locally; their bytes are not uploaded or retained by the app. Keep the original in the organization's evidence store and enter its reference. Gate-specific metadata is subject to the existing backend validators. Synthetic evidence never satisfies a real evidence gate. Review the current digest before signing; stale digests and maker self-approval are rejected. Decisions only update governance records; deployment, database restore and payment execution remain separate controlled operations. After an uncertain network result, review the audit trail before resubmitting.

The workflow proxy permits only fixed production-governance actions and integer release IDs, requires authentication and same-origin writes, and limits JSON records to 256 KiB. Recorded mode is read-only and cannot initiate login or submit mutations. The existing read proxy accepts the secure session cookie without exposing the token to client JavaScript.

## Hosting and persistence

The existing PostgreSQL production Compose configuration now requires a real password-bearing DATABASE_URL rather than the incomplete passwordless URL. Its migration service must complete before the API starts. IdP endpoints, backend hosts and frontend origin must be explicit. ALLOWED_HOSTS must include the external backend hostname, backend and 127.0.0.1 when using the reference containers. Put the database password in secrets/db_password.txt and supply a matching connection URL through the deployment secret store; never commit it. Serve the frontend and public backend over HTTPS. An internal container backend URL can remain http://backend:8000 on a private network. On Vercel, API_BASE_URL must point to the externally hosted HTTPS backend.

The readiness health check establishes service/database availability, not permission to execute treasury actions. The separate production release gate can remain blocked while users collect validation records. PostgreSQL uses a persistent named volume in the reference stack. A managed database should use its provider's automated backup and restore controls.

## Remaining external work

- Choose and provision the backend host and PostgreSQL service. No account, purchase or real deployment was performed for these services.
- Configure the real company IdP and active account roles, then verify sign-in, expiry, account disablement and distinct reviewers with that provider.
- Configure CONNECTOR_OIDC_ISSUER, CONNECTOR_OIDC_JWKS_URL and WORKLOAD_IDENTITY_AUDIENCE for the delivered JWT workload adapter. Its audience must differ from the user API audience. Register each exact JWT subject as an active SourceConnector with the correct BANK, ERP or MARKET type. Only the seven fixed ingestion endpoints accept workload tokens; claims must match the payload connector_code. Development headers stay rejected in production. Test this with the real workload issuer before provider ingestion.
- Connect licensed bank, ERP and market sources and reconcile representative company data before source promotion.
- Supply authorized AI access and verify the requested five-team model availability, latency, cost and routing. Existing AI remains disabled without these settings; no model call was made by this change.
- Execute PostgreSQL restore/failover and load tests in the target environment, connect monitoring to the actual operations destination, and collect independent model, security, UAT, legal/tax and release sign-offs.

The application remains a validation candidate, not a certified live treasury system.

Protocol references: [OpenID Connect](https://openid.net/specs/openid-connect-core-1_0.html), [Next.js cookie settings](https://nextjs.org/docs/app/api-reference/functions/cookies).
