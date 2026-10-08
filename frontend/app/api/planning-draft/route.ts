import { authorization, backend, demo, sameOrigin } from "../../../lib/session";

async function proxy(request: Request, write: boolean) {
  if (demo()) return Response.json({ error: "Saving needs your company backend and sign-in. The public demo keeps planning data only in this browser session." }, { status: 403 });
  if (!backend()) return Response.json({ error: "Company backend is not configured." }, { status: 503 });
  if (write && !sameOrigin(request)) return Response.json({ error: "Same-origin request required." }, { status: 403 });
  const auth = authorization(request);
  if (!auth) return Response.json({ error: "Company sign-in required." }, { status: 401 });
  let body: string | undefined;
  if (write) {
    if (!request.headers.get("content-type")?.startsWith("application/json")) return Response.json({ error: "JSON required." }, { status: 415 });
    const bytes = await request.arrayBuffer();
    if (bytes.byteLength > 524288) return Response.json({ error: "Draft too large." }, { status: 413 });
    body = new TextDecoder().decode(bytes);
    try { JSON.parse(body); } catch { return Response.json({ error: "Invalid JSON." }, { status: 400 }); }
  }
  try {
    const response = await fetch(`${backend()}/api/v1/company/planning-draft`, { method: write ? "PUT" : "GET", headers: { Authorization: auth, "Content-Type": "application/json" }, body, cache: "no-store", signal: AbortSignal.timeout(45000) });
    const result = await response.json();
    return Response.json(response.ok ? result : { error: typeof result.detail === "string" ? result.detail : "Check the draft inputs and your assigned role." }, { status: response.status, headers: { "Cache-Control": "no-store" } });
  } catch { return Response.json({ error: "Draft service unavailable. Load the saved version before retrying a save." }, { status: 502 }); }
}
export async function GET(request: Request) { return proxy(request, false); }
export async function PUT(request: Request) { return proxy(request, true); }
