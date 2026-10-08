import type { DemoSnapshot } from "./automatic-demo";
import type { Flow } from "./planning";

export type WarningEvidence = { reference: string; date?: string; summary: string };
export type WarningExplanation = { id: string; title: string; cause: string; evidence: WarningEvidence[]; nextStep: string };
const positive = (value: string) => Number(value) > 0;
const negative = (value: string) => Number(value) < 0;
const day = (value: string) => Date.parse(`${value}T00:00:00Z`) / 86400000;
const flowEvidence = (flows: Flow[]): WarningEvidence[] => flows.map(flow => ({ reference: flow.id, date: flow.date, summary: `${flow.entity} · ${flow.direction === "INFLOW" ? "Expected money in" : "Planned money out"} · ${flow.currency} ${flow.amount}` }));

// Explanations use the same supplied dummy snapshot as the position cards.
// Records are supporting inputs, not proof that a single invoice caused a gap.
export function explainWarnings(snapshot: DemoSnapshot | null): WarningExplanation[] | null {
  if (!snapshot) return null;
  const { positions: p, state, simulatedAsOf: date } = snapshot;
  const result: WarningExplanation[] = [];
  const cashEvidence: WarningEvidence[] = [
    ...Object.entries(state.balances).map(([currency, amount]) => ({ reference: `BANK-${currency}`, date, summary: `Dummy balance · ${currency} ${amount}` })),
    { reference: "CASH-ADJUSTMENTS", date, summary: `USD ${p.restricted} restricted and USD ${p.committed} committed cash deducted. No credit facilities included.` },
  ];
  if (negative(p.headroom)) result.push({ id: "cash", title: "Money available is below the minimum", cause: `Available cash is USD ${p.deployable}; the dummy minimum is USD ${p.buffer}. The difference is USD ${p.headroom}.`, evidence: cashEvidence, nextStep: "Check usable bank balances, restricted money and upcoming payments with your treasury team. This warning does not mean a payment has failed." });
  if (positive(p.forecast.maximumShortfall)) {
    const week = p.forecast.firstBreach!;
    const point = p.forecast.points.find(row => row.week === week)!;
    result.push({ id: "forecast", title: `Money may fall below the minimum in week ${week}`, cause: `Expected closing cash for the week starting ${point.date} is USD ${point.closing}, against a USD ${point.buffer} minimum. The biggest weekly gap in this plan is USD ${p.forecast.maximumShortfall}.`, evidence: [...cashEvidence, ...flowEvidence(state.flows.filter(flow => day(flow.date) >= day(date) && day(flow.date) < day(date) + week * 7))], nextStep: "Review the opening cash and all expected receipts and payments up to this week. Check collection dates and payment timing; staff must approve any financing or payment change. Weekly totals can hide shortages within a day." });
  }
  for (const hedge of p.hedges) {
    if (hedge.status === "WITHIN-POLICY" && !hedge.wrongDirection) continue;
    const evidence = [...flowEvidence(state.flows.filter(flow => flow.currency === hedge.currency)), ...state.hedges.filter(row => row.currency === hedge.currency).map(row => ({ reference: row.id, summary: `${row.direction} hedge · ${row.currency} ${row.amount} · No contract maturity supplied` }))];
    result.push({ id: `hedge-${hedge.currency}`, title: `${hedge.currency} currency protection needs review`, cause: `Open net receipts or payments are ${hedge.currency} ${hedge.underlying}; the existing signed hedge is ${hedge.hedge}. ${hedge.ratio === null ? "There is no matching net invoice exposure." : `Coverage by amount is ${hedge.ratio}%; this example uses a 60–90% range.`} ${hedge.wrongDirection ? "The hedge now points in the same direction as the open exposure." : `The amount check is ${hedge.status.toLowerCase().replaceAll("-", " ")}.`} Remaining signed exposure is ${hedge.residual}; this is an amount affected by currency changes, not a predicted loss.`, evidence, nextStep: "Check invoice currency, timing and existing hedge contracts with an authorised treasury reviewer. This group check is against USD and includes invoices outside the cash forecast. It does not measure contract timing, valuation or each entity’s currency policy; no trade is proposed or placed." });
  }
  if (!state.marketHealthy) result.push({ id: "market", title: "The exchange-rate update failed", cause: `Conversions use the last validated dummy EUR rate ${state.rates.EUR} and GBP rate ${state.rates.GBP} USD per currency unit. These are fictional test prices; a successful quote timestamp is unavailable.`, evidence: snapshot.history.filter(row => row.outcome === "QUARANTINED" && row.source === "MARKET").map(row => ({ reference: row.id, summary: `Rejected event ${row.cycle}: ${row.reason}` })), nextStep: "Check the rejected market update and obtain a validated replacement. Treat converted figures as using old prices until a valid update succeeds." });
  if (p.forecast.beyond || p.forecast.overdue) result.push({ id: "excluded", title: "Some invoices are outside this cash plan", cause: `${p.forecast.overdue} records are before the fictional planning date and ${p.forecast.beyond} are outside the next 13 weeks. They are excluded from weekly cash totals but remain in open currency exposure.`, evidence: flowEvidence(state.flows.filter(flow => day(flow.date) < day(date) || day(flow.date) >= day(date) + 91)), nextStep: "Check whether old invoices were settled and whether future due dates are correct. Extend or correct a planning scenario after review; do not treat missing dates as received money." });
  if (snapshot.scope === "mnc") for (const entity of p.entities.filter(row => negative(row.headroom) || positive(row.maximumShortfall))) result.push({ id: `entity-${entity.id}`, title: `${entity.name} needs its own cash review`, cause: `${entity.country} entity ${entity.id} has local available cash ${entity.functionalCurrency} ${entity.deployableLocal}. Its current difference from the minimum is USD ${entity.headroom}; its biggest forecast gap is USD ${entity.maximumShortfall}. Group money is not automatically available to this entity.`, evidence: [{ reference: entity.id, date, summary: `Entity position · minimum USD ${entity.buffer}` }, ...flowEvidence(state.flows.filter(flow => flow.entity === entity.id))], nextStep: "Check this entity’s accounts and obligations separately. Any transfer between companies or countries needs the relevant legal, tax and human approvals." });
  const rejected = snapshot.history.filter(row => row.outcome === "QUARANTINED");
  if (rejected.length) result.push({ id: "rejected", title: "Some incoming records were kept out", cause: `${rejected.length} dummy events failed validation. They did not replace the last good position; they remain listed even if a later update recovers.`, evidence: rejected.map(row => ({ reference: row.id, summary: `${row.source} · event ${row.cycle} · ${row.reason}` })), nextStep: "Review each reference and its stated problem at the source. Correct and reconcile the data through the approved process before retrying. A rejected record is not proof that the underlying transaction did not happen." });
  return result;
}
