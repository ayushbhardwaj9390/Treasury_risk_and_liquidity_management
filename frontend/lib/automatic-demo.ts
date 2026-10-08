// Synthetic-only, stateless simulation. Never reads or writes company data.
import source from "./dummy-feed.json";
import { decimal, dollars, simulate, validDate, type Flow } from "./planning";

const scale = 10n ** 32n;
const abs = (value: bigint) => value < 0n ? -value : value;
const multiply = (a: bigint, b: bigint) => a * b / scale;
const signed = (value: string) => value.startsWith("-") ? -decimal(value.slice(1), 2) : decimal(value, 2);
type Hedge = { id: string; currency: string; direction: string; amount: string };
export type DemoScope = "single" | "mnc";
export function entityDefinitions(scope: DemoScope) {
  return scope === "mnc" ? source.multinational.entities : [{ id: "DEMO", name: "Harbor Manufacturing US", country: "US", functionalCurrency: "USD", bankCurrencies: ["USD", "EUR", "GBP"], buffer: source.buffer, restricted: source.restricted, committed: source.committed }];
}
export type DemoState = { balances: Record<string, string>; rates: Record<string, string>; flows: Flow[]; hedges: Hedge[]; marketHealthy: boolean; marketSequence: number; lastSequence: number; seen: Record<string, string> };
export type DemoEvent = { id: string; sequence: number; source: string; kind: string; title: string; flow?: string; amount?: string; rates?: Record<string, string>; invoice?: Flow; date?: string };
export type EventRecord = { cycle: number; id: string; source: string; title: string; outcome: "APPLIED" | "DUPLICATE" | "QUARANTINED"; reason: string };
export const totalCycles = source.events.length;
export function initialState(scope: DemoScope = "single"): DemoState {
  return { balances: { ...source.balances }, rates: { ...source.rates }, flows: source.flows.map(flow => ({ ...flow, entity: scope === "single" ? "DEMO" : entityDefinitions(scope).find(entity => entity.bankCurrencies.includes(flow.currency))!.id } as Flow)), hedges: source.hedges.map(hedge => ({ ...hedge })), marketHealthy: true, marketSequence: 0, lastSequence: 0, seen: {} };
}
export function applyEvent(current: DemoState, event: DemoEvent, cycle: number): { state: DemoState; record: EventRecord } {
  const record = (outcome: EventRecord["outcome"], reason: string) => ({ cycle, id: event.id, source: event.source, title: event.title, outcome, reason });
  const fingerprint = JSON.stringify(event);
  if (current.seen[event.id] === fingerprint) return { state: current, record: record("DUPLICATE", "Already processed; cash and exposure unchanged.") };
  const state: DemoState = structuredClone(current);
  try {
    if (current.seen[event.id]) throw Error("Reference reused with a different payload.");
    if (!Number.isSafeInteger(event.sequence) || event.sequence <= current.lastSequence) throw Error("Out-of-order update rejected.");
    if (event.kind === "MARKET") {
      if (!event.rates || Object.keys(event.rates).sort().join(",") !== "EUR,GBP") throw Error("Both supported dummy market currencies are required.");
      for (const rate of Object.values(event.rates)) if (decimal(rate) <= 0n || decimal(rate) > decimal("100")) throw Error("Invalid exchange rate.");
      state.rates = { ...event.rates }; state.marketHealthy = true; state.marketSequence = event.sequence;
    } else if (event.kind === "INVOICE") {
      const flow = event.invoice;
      if (!flow || state.flows.some(row => row.id === flow.id) || !["USD", "EUR", "GBP"].includes(flow.currency)
        || !validDate(flow.date) || !["INFLOW", "OUTFLOW"].includes(flow.direction) || decimal(flow.amount, 2) <= 0n || flow.probability !== "1") throw Error("Invalid or duplicate invoice.");
      state.flows.push({ ...flow });
    } else if (event.kind === "SETTLEMENT" || event.kind === "DUE_DATE") {
      const index = state.flows.findIndex(flow => flow.id === event.flow);
      if (index < 0) throw Error("Invoice reference is not open or mapped.");
      const flow = state.flows[index];
      if (event.kind === "DUE_DATE") {
        if (!event.date || !validDate(event.date)) throw Error("Invalid invoice due date.");
        state.flows[index] = { ...flow, date: event.date };
      } else {
        if (!event.amount || decimal(event.amount, 2) !== decimal(flow.amount, 2)) throw Error("Settlement does not reconcile to invoice amount.");
        const amount = decimal(flow.amount, 2) * (flow.direction === "INFLOW" ? 1n : -1n);
        state.balances[flow.currency] = dollars(signed(state.balances[flow.currency]) + amount);
        state.flows.splice(index, 1);
      }
    } else throw Error("Unsupported dummy event.");
    state.seen[event.id] = fingerprint; state.lastSequence = event.sequence;
    return { state, record: record("APPLIED", "Dummy data validated; all positions recalculated together.") };
  } catch (error) {
    // A failed quote must not appear current; preserve all last validated amounts.
    const rejected = structuredClone(current);
    if (event.kind === "MARKET") rejected.marketHealthy = false;
    return { state: rejected, record: record("QUARANTINED", (error as Error).message) };
  }
}
export function calculatePositions(state: DemoState, scope: DemoScope = "single") {
  const rate = (currency: string) => decimal(currency === "USD" ? "1" : state.rates[currency]);
  const assumptions = { start: source.start, weeks: 13, rates: state.rates, delay: 0, receipts: 0, costs: 0, oil: 0, fx: 0 };
  const entities = entityDefinitions(scope).map(entity => {
    const grossLocal = entity.bankCurrencies.reduce((sum, currency) => sum + multiply(signed(state.balances[currency]), currency === entity.functionalCurrency ? scale : rate(currency) * scale / rate(entity.functionalCurrency)), 0n);
    const deployableLocal = grossLocal - decimal(entity.restricted) - decimal(entity.committed);
    const deployable = multiply(deployableLocal, rate(entity.functionalCurrency));
    const buffer = multiply(decimal(entity.buffer), rate(entity.functionalCurrency));
    const forecast = simulate(state.flows.filter(flow => flow.entity === entity.id), { ...assumptions, opening: dollars(deployable), buffer: dollars(buffer) });
    return { id: entity.id, name: entity.name, country: entity.country, functionalCurrency: entity.functionalCurrency, deployableLocal: dollars(deployableLocal), deployable: dollars(deployable), buffer: dollars(buffer), headroom: dollars(deployable - buffer), maximumShortfall: forecast.maximumShortfall, firstBreach: forecast.firstBreach };
  });
  const gross = Object.entries(state.balances).reduce((sum, [currency, amount]) => sum + multiply(signed(amount), rate(currency)), 0n);
  const restricted = entityDefinitions(scope).reduce((sum, entity) => sum + multiply(decimal(entity.restricted), rate(entity.functionalCurrency)), 0n);
  const committed = entityDefinitions(scope).reduce((sum, entity) => sum + multiply(decimal(entity.committed), rate(entity.functionalCurrency)), 0n);
  const buffer = entities.reduce((sum, entity) => sum + decimal(entity.buffer, 2), 0n);
  const deployable = gross - restricted - committed;
  const forecast = simulate(state.flows, { ...assumptions, opening: dollars(deployable), buffer: dollars(buffer) });
  const hedges = ["EUR", "GBP"].map(currency => {
    const underlying = state.flows.filter(flow => flow.currency === currency).reduce((sum, flow) => sum + decimal(flow.amount, 2) * (flow.direction === "INFLOW" ? 1n : -1n), 0n);
    const hedge = state.hedges.filter(row => row.currency === currency).reduce((sum, row) => sum + decimal(row.amount, 2) * (row.direction === "BUY" ? 1n : -1n), 0n);
    const ratio = underlying === 0n ? null : abs(hedge) * scale / abs(underlying);
    const status = underlying === 0n ? (hedge === 0n ? "NO_EXPOSURE" : "UNMATCHED") : abs(hedge) > multiply(abs(underlying), decimal("1.05")) ? "OVER-HEDGED" : ratio! < decimal("0.60") ? "UNDER-HEDGED" : ratio! > decimal("0.90") ? "ABOVE-POLICY" : "WITHIN-POLICY";
    return { currency, underlying: dollars(underlying), hedge: dollars(hedge), residual: dollars(underlying + hedge), ratio: ratio === null ? null : dollars(multiply(ratio > decimal("9.999999") ? decimal("9.999999") : ratio, decimal("100"))), status, wrongDirection: underlying !== 0n && hedge !== 0n && (underlying > 0n) === (hedge > 0n) };
  });
  const residual = hedges.reduce((sum, hedge) => sum + multiply(abs(signed(hedge.residual)), rate(hedge.currency)), 0n);
  const alerts = [
    ...(deployable < buffer ? ["Available cash is below the dummy minimum buffer."] : []),
    ...(decimal(forecast.maximumShortfall, 2) > 0n ? [`Forecast cash falls below the dummy buffer in week ${forecast.firstBreach}.`] : []),
    ...hedges.filter(hedge => hedge.status !== "WITHIN-POLICY").map(hedge => `${hedge.currency}: ${hedge.status.toLowerCase().replaceAll("-", " ")}. Review the existing hedge; no trade has been placed.`),
    ...hedges.filter(hedge => hedge.wrongDirection).map(hedge => `${hedge.currency}: the existing hedge is now in the same direction as exposure. Human review required.`),
    ...(!state.marketHealthy ? ["Market refresh failed. Values use the last validated dummy rates; they are not current market prices."] : []),
    ...(forecast.beyond ? [`${forecast.beyond} receipt(s) fall beyond the 13-week forecast; they remain in open FX exposure.`] : []),
    ...(scope === "mnc" ? entities.filter(entity => signed(entity.headroom) < 0n || decimal(entity.maximumShortfall, 2) > 0n).map(entity => `${entity.name}: local cash or forecast buffer pressure requires entity-level review. Group cash does not authorize a cross-border transfer.`) : []),
  ];
  return { gross: dollars(gross), restricted: dollars(restricted), committed: dollars(committed), deployable: dollars(deployable), buffer: dollars(buffer), headroom: dollars(deployable - buffer), residualUsd: dollars(residual), forecast, hedges, entities, alerts };
}
export function demoSnapshot(cycle: number, scope: DemoScope = "single") {
  if (!["single", "mnc"].includes(scope)) throw Error("Invalid dummy company scope.");
  if (!Number.isSafeInteger(cycle) || cycle < 0 || cycle > totalCycles) throw Error("Invalid dummy cycle.");
  let state = initialState(scope); const history: EventRecord[] = [];
  for (let index = 0; index < cycle; index++) {
    const event = structuredClone(source.events[index]) as DemoEvent;
    if (event.invoice) event.invoice.entity = scope === "single" ? "DEMO" : entityDefinitions(scope).find(entity => entity.bankCurrencies.includes(event.invoice!.currency))!.id;
    const result = applyEvent(state, event, index + 1); state = result.state; history.push(result.record);
  }
  return { mode: "SYNTHETIC_AUTOMATION" as const, scope, company: scope === "mnc" ? source.multinational.company : source.company, simulatedAsOf: source.start, cycle, totalCycles, state, history, positions: calculatePositions(state, scope), executionEnabled: false as const };
}
export type DemoSnapshot = ReturnType<typeof demoSnapshot>;
