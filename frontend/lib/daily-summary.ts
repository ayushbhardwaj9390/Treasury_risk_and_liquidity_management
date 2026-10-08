import type { DemoSnapshot } from "./automatic-demo";
import { decimal, dollars, validDate, type Flow } from "./planning";

const signed = (value: string) => value.startsWith("-") ? -decimal(value.slice(1), 2) : decimal(value, 2);
export type CurrencyTotal = { currency: string; amount: string; count: number };
function totals(flows: Flow[]): CurrencyTotal[] {
  const grouped = new Map<string, { amount: bigint; count: number }>();
  for (const flow of flows) {
    const prior = grouped.get(flow.currency) ?? { amount: 0n, count: 0 };
    grouped.set(flow.currency, { amount: prior.amount + decimal(flow.amount, 2), count: prior.count + 1 });
  }
  return [...grouped.entries()].sort(([a], [b]) => a.localeCompare(b)).map(([currency, value]) => ({ currency, amount: dollars(value.amount), count: value.count }));
}

// A view of supplied, validated synthetic records; never changes or executes them.
export function buildDailySummary(snapshot: DemoSnapshot | null) {
  if (!snapshot) return { available: false as const, reason: "No checked snapshot is available. Open automatic updates to inspect the fictional example." };
  try {
    if (snapshot.mode !== "SYNTHETIC_AUTOMATION" || !validDate(snapshot.simulatedAsOf)) throw Error("Missing scope or date.");
    const asOf = snapshot.simulatedAsOf;
    const end = new Date(Date.parse(`${asOf}T00:00:00Z`) + 6 * 86400000).toISOString().slice(0, 10);
    for (const flow of snapshot.state.flows) {
      if (!validDate(flow.date) || !/^[A-Z]{3}$/.test(flow.currency) || !["INFLOW", "OUTFLOW"].includes(flow.direction) || decimal(flow.amount, 2) <= 0n) throw Error("Unchecked cash-flow record.");
    }
    const upcoming = snapshot.state.flows.filter(flow => flow.date >= asOf && flow.date <= end);
    const overdue = snapshot.state.flows.filter(flow => flow.date < asOf).map(flow => ({ ...flow })).sort((a, b) => a.date.localeCompare(b.date) || a.id.localeCompare(b.id));
    const cash = signed(snapshot.positions.deployable), minimum = decimal(snapshot.positions.buffer, 2);
    return {
      available: true as const, company: snapshot.company, asOf, end, cycle: snapshot.cycle, marketHealthy: snapshot.state.marketHealthy,
      cash: dollars(cash), minimum: dollars(minimum), gap: dollars(cash < minimum ? minimum - cash : 0n),
      incoming: totals(upcoming.filter(flow => flow.direction === "INFLOW")), outgoing: totals(upcoming.filter(flow => flow.direction === "OUTFLOW")), overdue,
      entitiesNeedingReview: snapshot.positions.entities.filter(entity => signed(entity.headroom) < 0n || decimal(entity.maximumShortfall, 2) > 0n).map(entity => entity.name),
    };
  } catch {
    return { available: false as const, reason: "This snapshot is incomplete or invalid. No money summary is shown; review the source records first." };
  }
}
