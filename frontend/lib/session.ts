import { createHmac, randomBytes, createHash, timingSafeEqual } from "node:crypto";

export const sessionCookie = "__Host-treasury-session";
export const flowCookie = "__Host-treasury-flow";
export function cookie(request: Request, name: string) {
  return request.headers.get("cookie")?.split(";").map(x => x.trim()).find(x => x.startsWith(`${name}=`))?.slice(name.length + 1);
}
export function authorization(request: Request) {
  const token = cookie(request, sessionCookie);
  return request.headers.get("authorization") ?? (token ? `Bearer ${token}` : undefined);
}
export function backend() { return process.env.API_BASE_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL; }
export function demo() { return process.env.TREASURY_DEMO_MODE === "recorded" || (process.env.VERCEL === "1" && !backend()); }
export function sameOrigin(request: Request) {
  const expected = process.env.APP_URL ?? new URL(request.url).origin;
  return request.headers.get("origin") === new URL(expected).origin;
}
export function loginConfig() {
  const { APP_URL, OIDC_CLIENT_ID, OIDC_AUTHORIZATION_URL, OIDC_TOKEN_URL, OIDC_CLIENT_SECRET, SESSION_SECRET } = process.env;
  if (demo() || !backend() || !APP_URL || !OIDC_CLIENT_ID || !OIDC_AUTHORIZATION_URL || !OIDC_TOKEN_URL || !SESSION_SECRET || SESSION_SECRET.length < 32) return null;
  try { if (![APP_URL, OIDC_AUTHORIZATION_URL, OIDC_TOKEN_URL].every(x => new URL(x).protocol === "https:")) return null; } catch { return null; }
  return { app: new URL(APP_URL).origin, client: OIDC_CLIENT_ID, authorize: OIDC_AUTHORIZATION_URL, token: OIDC_TOKEN_URL, secret: OIDC_CLIENT_SECRET, signing: SESSION_SECRET };
}
export function newFlow(secret: string) {
  const state = randomBytes(32).toString("base64url"), verifier = randomBytes(32).toString("base64url");
  const data = Buffer.from(JSON.stringify({ state, verifier, expires: Date.now() + 600000 })).toString("base64url");
  return { state, verifier, challenge: createHash("sha256").update(verifier).digest("base64url"), value: `${data}.${createHmac("sha256", secret).update(data).digest("base64url")}` };
}
export function readFlow(value: string | undefined, state: string | null, secret: string) {
  try {
    const [data, mac, extra] = (value ?? "").split(".");
    const expected = createHmac("sha256", secret).update(data).digest();
    const received = Buffer.from(mac, "base64url");
    if (extra || expected.length !== received.length || !timingSafeEqual(expected, received)) return null;
    const flow = JSON.parse(Buffer.from(data, "base64url").toString());
    return flow.state === state && flow.expires > Date.now() ? flow : null;
  } catch { return null; }
}
