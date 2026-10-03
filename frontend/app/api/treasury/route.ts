import endpoints from "../../../lib/endpoints.json";
import snapshot from "../../../lib/demo-snapshot.json";

export async function GET(request: Request) {
  const key = new URL(request.url).searchParams.get("key") ?? "";
  const catalog: Record<string, { path: string }> = endpoints;
  const path = key === "productionGate" ? "/health/production" : catalog[key]?.path;
  if (!path) return Response.json({ error: "Unknown workspace" }, { status: 400 });
  const backendConfigured = process.env.API_BASE_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL;
  const recordedDemo = process.env.TREASURY_DEMO_MODE === "recorded"
    || (process.env.VERCEL === "1" && !backendConfigured);
  if (recordedDemo) {
    const data: Record<string, unknown> = snapshot.results;
    if (!Object.hasOwn(data, key)) return Response.json({ error: "No recorded demo for this analysis" }, { status: 404 });
    return Response.json(data[key], { headers: {
      "Cache-Control": "no-store", "X-Treasury-Data-Mode": "recorded-demo",
      "X-Treasury-Data-As-Of": snapshot.captured_at,
    } });
  }
  const headers = new Headers();
  const authorization = request.headers.get("authorization");
  if (authorization) headers.set("Authorization", authorization);
  try {
    const base = backendConfigured ?? "http://127.0.0.1:8000";
    const upstream = await fetch(`${base}${path}`, {
      cache: "no-store", headers, signal: AbortSignal.timeout(45000),
    });
    if (!upstream.ok && !(key === "productionGate" && upstream.status === 503)) {
      return Response.json({ error: [401, 403].includes(upstream.status)
        ? "Sign in through your enterprise identity provider to view this workspace."
        : "This analysis is temporarily unavailable. Retry this workspace.", status: upstream.status },
        { status: upstream.status });
    }
    return Response.json(await upstream.json(), { headers: { "Cache-Control": "no-store" } });
  } catch {
    return Response.json({ error: "Cannot reach the treasury service. Check that the backend is running, then retry." },
      { status: 502 });
  }
}
