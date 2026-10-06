import { authorization, backend, demo, sameOrigin } from "../../../lib/session";

const operations: Record<string, string> = { create: "releases", evidence: "evidence", observation: "observations", signoff: "signoffs", transition: "transitions", benchmark: "model-benchmark" };
async function proxy(request: Request, write: boolean) {
  if (demo()) return Response.json({ error: "Recorded demonstration is read-only. Connect an authenticated backend to save records." }, { status: 403 });
  if (!backend()) return Response.json({ error: "A hosted treasury backend is required." }, { status: 503 });
  if (write && !sameOrigin(request)) return Response.json({ error: "Same-origin request required" }, { status: 403 });
  const auth = authorization(request);
  if (!auth) return Response.json({ error: "Company sign-in required." }, { status: 401 });
  const query = new URL(request.url).searchParams, action = query.get("action") ?? "", id = query.get("release");
  if (!write && !["status", "events"].includes(action) || write && !operations[action]) return Response.json({ error: "Unknown workflow" }, { status: 400 });
  if (!["create", "benchmark"].includes(action) && !/^[1-9]\d{0,9}$/.test(id ?? "")) return Response.json({ error: "Select a valid release." }, { status: 400 });
  const path = action === "create" || action === "benchmark" ? operations[action] : `releases/${id}${action === "status" ? "" : `/${write ? operations[action] : "events"}`}`;
  let body: string | undefined;
  if (write) {
    if (!request.headers.get("content-type")?.startsWith("application/json")) return Response.json({ error: "JSON required" }, { status: 415 });
    const bytes = await request.arrayBuffer();
    if (bytes.byteLength > 262144) return Response.json({ error: "Record too large" }, { status: 413 });
    body = new TextDecoder().decode(bytes);
    try { JSON.parse(body); } catch { return Response.json({ error: "Invalid JSON" }, { status: 400 }); }
  }
  try {
    const response = await fetch(`${backend()}/api/v1/production/${path}`, { method: write ? "POST" : "GET", headers: { Authorization: auth, "Content-Type": "application/json" }, body, cache: "no-store", signal: AbortSignal.timeout(45000) });
    const result = await response.json();
    return Response.json(response.ok ? result : { error: typeof result.detail === "string" ? result.detail : "Check the required fields and your assigned role." }, { status: response.status, headers: { "Cache-Control": "no-store" } });
  } catch { return Response.json({ error: "Treasury service unavailable. Check the release audit trail before retrying a submission." }, { status: 502 }); }
}
export async function GET(request: Request) { return proxy(request, false); }
export async function POST(request: Request) { return proxy(request, true); }
