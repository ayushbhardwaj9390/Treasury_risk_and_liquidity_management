import { NextResponse } from "next/server";
import { authorization, backend, cookie, demo, flowCookie, loginConfig, newFlow, readFlow, sameOrigin, sessionCookie } from "../../../../lib/session";

type Context = { params: Promise<{ action: string }> };
const options = { httpOnly: true, secure: true, sameSite: "lax" as const, path: "/" };
export async function GET(request: Request, context: Context) {
  const { action } = await context.params;
  const config = loginConfig();
  if (action === "session") {
    const auth = authorization(request);
    if (!auth || !backend() || demo()) return NextResponse.json({ authenticated: false, loginAvailable: Boolean(config), recordedDemo: demo() }, { headers: { "Cache-Control": "no-store" } });
    try {
      const response = await fetch(`${backend()}/api/v1/production/identity`, { headers: { Authorization: auth }, cache: "no-store", signal: AbortSignal.timeout(10000) });
      if (!response.ok) return NextResponse.json({ authenticated: false, loginAvailable: Boolean(config), error: "Your session expired or your account has no active treasury role." }, { status: response.status, headers: { "Cache-Control": "no-store" } });
      return NextResponse.json({ authenticated: true, ...(await response.json()) }, { headers: { "Cache-Control": "no-store" } });
    } catch { return NextResponse.json({ error: "Sign-in service unavailable." }, { status: 502 }); }
  }
  if (!config) return NextResponse.json({ error: "Company sign-in is not configured. The demonstration remains read-only." }, { status: 503 });
  if (action === "login") {
    const flow = newFlow(config.signing), target = new URL(config.authorize);
    Object.entries({ response_type: "code", client_id: config.client, redirect_uri: `${config.app}/api/auth/callback`, scope: "openid profile email", state: flow.state, code_challenge: flow.challenge, code_challenge_method: "S256" }).forEach(([k, v]) => target.searchParams.set(k, v));
    const response = NextResponse.redirect(target);
    response.cookies.set(flowCookie, flow.value, { ...options, maxAge: 600 });
    return response;
  }
  if (action !== "callback") return NextResponse.json({ error: "Unknown sign-in action" }, { status: 404 });
  const query = new URL(request.url).searchParams, flow = readFlow(cookie(request, flowCookie), query.get("state"), config.signing);
  const failed = () => { const response = NextResponse.redirect(`${config.app}/?signin=failed`); response.cookies.set(flowCookie, "", { ...options, maxAge: 0 }); return response; };
  if (!flow || !query.get("code") || query.has("error")) return failed();
  try {
    const body = new URLSearchParams({ grant_type: "authorization_code", code: query.get("code")!, client_id: config.client, redirect_uri: `${config.app}/api/auth/callback`, code_verifier: flow.verifier });
    if (config.secret) body.set("client_secret", config.secret);
    const tokens = await fetch(config.token, { method: "POST", body, signal: AbortSignal.timeout(10000), cache: "no-store" });
    if (!tokens.ok) return failed();
    const result = await tokens.json();
    // Only a JWT access token verified by the treasury backend establishes a session.
    if (typeof result.access_token !== "string" || result.access_token.length > 3500) return failed();
    const identity = await fetch(`${backend()}/api/v1/production/identity`, { headers: { Authorization: `Bearer ${result.access_token}` }, cache: "no-store", signal: AbortSignal.timeout(10000) });
    if (!identity.ok) return failed();
    const response = NextResponse.redirect(config.app);
    response.cookies.set(sessionCookie, result.access_token, { ...options, maxAge: Math.min(3600, Math.max(1, Number(result.expires_in) || 300)) });
    response.cookies.set(flowCookie, "", { ...options, maxAge: 0 });
    return response;
  } catch { return failed(); }
}
export async function POST(request: Request, context: Context) {
  if ((await context.params).action !== "logout") return NextResponse.json({ error: "Unknown action" }, { status: 404 });
  if (!sameOrigin(request)) return NextResponse.json({ error: "Same-origin request required" }, { status: 403 });
  const response = NextResponse.json({ signedOut: true });
  response.cookies.set(sessionCookie, "", { ...options, maxAge: 0 });
  response.cookies.set(flowCookie, "", { ...options, maxAge: 0 });
  return response;
}
