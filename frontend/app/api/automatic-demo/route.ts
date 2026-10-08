import { demoSnapshot, totalCycles } from "../../../lib/automatic-demo";

// Public synthetic endpoint. No company input, credentials, uploads or backend writes.
export async function GET(request: Request) {
  const query = new URL(request.url).searchParams;
  const cycle = query.get("cycle") ?? "0";
  const scope = query.get("scope") ?? "single";
  if ([...query.keys()].some(key => !["cycle", "scope"].includes(key)) || query.getAll("cycle").length > 1 || query.getAll("scope").length > 1 || !["single", "mnc"].includes(scope) || !/^(0|[1-9]\d?)$/.test(cycle) || Number(cycle) > totalCycles) return Response.json({ error: "Choose a valid dummy structure and update cycle." }, { status: 400 });
  return Response.json({ ...demoSnapshot(Number(cycle), scope as "single" | "mnc"), calculatedAt: new Date().toISOString() }, { headers: { "Cache-Control": "no-store", "X-Treasury-Data-Mode": "synthetic-automation" } });
}
