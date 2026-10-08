"use client";
import { useEffect, useRef, useState } from "react";
import type { DemoSnapshot, DemoScope } from "../lib/automatic-demo";

type Snapshot = DemoSnapshot & { calculatedAt: string };
const money = (value: string) => new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(Number(value));
const amount = (value: string) => new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 }).format(Number(value));

export default function AutomaticUpdates({ active }: { active: boolean }) {
  const [scope, setScope] = useState<DemoScope>("single");
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [running, setRunning] = useState(false), [busy, setBusy] = useState(false), [message, setMessage] = useState("");
  const generation = useRef(0), request = useRef<AbortController | null>(null);
  function pause() { generation.current++; request.current?.abort(); setBusy(false); setRunning(false); }
  async function load(cycle: number) {
    request.current?.abort(); const controller = new AbortController(); request.current = controller;
    const id = ++generation.current; setBusy(true); setMessage("");
    const timeout = setTimeout(() => controller.abort(), 15000);
    try {
      const response = await fetch(`/api/automatic-demo?cycle=${cycle}&scope=${scope}`, { cache: "no-store", signal: controller.signal });
      const value = await response.json();
      if (!response.ok) throw Error(value.error ?? "Dummy calculation service unavailable.");
      if (value.mode !== "SYNTHETIC_AUTOMATION" || value.cycle !== cycle || value.scope !== scope || value.executionEnabled !== false) throw Error("Unexpected update. Last displayed positions were retained.");
      if (id !== generation.current) return;
      setSnapshot(value); if (value.cycle === value.totalCycles) setRunning(false);
    } catch (error) {
      if (id === generation.current) { setRunning(false); setMessage(`${controller.signal.aborted ? "Dummy update timed out." : (error as Error).message} Automatic updates paused; retry the same cycle. ${snapshot ? "Displayed positions are the last successful snapshot." : "No dummy position has been loaded yet."}`); }
    } finally { clearTimeout(timeout); if (id === generation.current) setBusy(false); }
  }
  useEffect(() => {
    load(0);
    const hidden = () => { if (document.hidden) { pause(); setMessage("Updates paused while this tab was hidden. Start again when you are ready."); } };
    document.addEventListener("visibilitychange", hidden);
    return () => { generation.current++; request.current?.abort(); document.removeEventListener("visibilitychange", hidden); };
  }, [scope]);
  useEffect(() => { if (!active) pause(); }, [active]);
  useEffect(() => {
    if (!active || !running || busy || !snapshot || snapshot.cycle >= snapshot.totalCycles) return;
    const timer = setTimeout(() => load(snapshot.cycle + 1), 5000);
    return () => clearTimeout(timer);
  }, [active, running, busy, snapshot]);
  const positions = snapshot?.positions, done = Boolean(snapshot && snapshot.cycle === snapshot.totalCycles);
  return <section className="automatic-workspace">
    <article className="panel"><p className="eyebrow">AUTOMATIC UPDATES · DUMMY DATA ONLY</p><h2>Watch the treasury position change</h2><p>Start the fictional company’s feed. Five seconds after each refresh, the next dummy bank, invoice or exchange-rate event updates cash, forecast pressure and hedge coverage together.</p><div className="demo-notice"><div><strong>Fresh dummy calculations · real connections disabled</strong><p>No confidential data is needed or accepted here. This example uses a separate fictional company. It does not change your uploads, the recorded dashboard, approved forecasts or production gates. No trade or payment is executed.</p></div></div>
      <label className="company-form">Operating structure<select value={scope} onChange={event => { pause(); setSnapshot(null); setMessage(""); setScope(event.target.value as DemoScope); }}><option value="single">Single-country company · United States</option><option value="mnc">Multinational group · US, Germany and UK</option></select></label><p className="muted">Both examples report in USD. A single-country business can still have foreign-currency transactions. Changing structure restarts the fictional feed.</p>
      <div className="automatic-controls"><button className="button secondary" disabled={(!running && busy) || !snapshot || done} onClick={() => { if (running) pause(); else { setMessage(""); setRunning(true); } }}>{running ? "Pause updates" : "Start automatic updates"}</button><button className="button secondary" disabled={busy || !snapshot || done} onClick={() => { pause(); load((snapshot?.cycle ?? 0) + 1); }}>Process next dummy event</button><button className="button secondary" disabled={busy} onClick={() => { pause(); load(0); }}>{snapshot ? "Restart dummy example" : "Retry initial snapshot"}</button></div>
      <p role="status" aria-live="polite">{busy ? "Recalculating the complete position…" : running ? "Running · next dummy event in five seconds" : done ? "Dummy feed complete. Restart to replay from the original balances." : "Paused · start automatic updates or process one event."} {message}</p>
      {snapshot && <p className="muted">{snapshot.company} · Event {snapshot.cycle} of {snapshot.totalCycles} · Fictional planning date {snapshot.simulatedAsOf} · Calculated {new Date(snapshot.calculatedAt).toLocaleTimeString()}. This runs while this workspace is open; it is not a background bank connection.</p>}
    </article>
    {snapshot && positions && <>
      {!snapshot.state.marketHealthy && <div className="inline-error" role="alert">Dummy market refresh failed. Cash conversions, forecasts and FX exposure use the last validated rates. A rejected quote never replaces them.</div>}
      <div className="automatic-metrics">
        <article className="panel"><p className="eyebrow">AVAILABLE CASH · USD</p><h2>{money(positions.deployable)}</h2><p>After {money(positions.restricted)} restricted cash and {money(positions.committed)} commitments.</p></article>
        <article className="panel"><p className="eyebrow">CASH BUFFER HEADROOM</p><h2>{money(positions.headroom)}</h2><p>Available cash less the dummy {money(positions.buffer)} minimum. No credit facilities assumed.</p></article>
        <article className="panel"><p className="eyebrow">MAXIMUM FORECAST SHORTFALL</p><h2>{money(positions.forecast.maximumShortfall)}</h2><p>{positions.forecast.firstBreach ? `First buffer breach: week ${positions.forecast.firstBreach}.` : "No weekly cash buffer breach in this snapshot."}</p></article>
        <article className="panel"><p className="eyebrow">RESIDUAL FX EXPOSURE · USD</p><h2>{money(positions.residualUsd)}</h2><p>Sum of absolute EUR and GBP exposure after existing dummy hedges. This is exposure, not a predicted loss or VaR.</p></article>
      </div>
      <div className="company-columns"><article className="panel"><h2>What needs attention?</h2><p className="muted">Calculated checks against this example’s cash buffer and 60–90% hedge range. These are dummy assumptions, not your company’s approved policy.</p>{positions.alerts.length ? <ul className="bullet-list">{positions.alerts.map(alert => <li key={alert}>{alert}</li>)}</ul> : <p>No configured dummy buffer or hedge-coverage breach. Production remains blocked by external evidence.</p>}</article>
        <article className="panel"><h2>Data checks</h2><dl className="detail-grid"><div><dt>Applied events</dt><dd>{snapshot.history.filter(row => row.outcome === "APPLIED").length}</dd></div><div><dt>Duplicates ignored</dt><dd>{snapshot.history.filter(row => row.outcome === "DUPLICATE").length}</dd></div><div><dt>Quarantined events</dt><dd>{snapshot.history.filter(row => row.outcome === "QUARANTINED").length}</dd></div><div><dt>Market refresh</dt><dd>{snapshot.state.marketHealthy ? "Validated dummy quote" : "Failed · last validated quote retained"}</dd></div></dl><p className="muted">EUR → USD {snapshot.state.rates.EUR} · GBP → USD {snapshot.state.rates.GBP}. Prices are fabricated for testing. Existing dummy hedge notionals stay unchanged; staff would review and approve any real adjustment.</p></article></div>
      <article className="panel"><h2>{scope === "mnc" ? "Country entities and group position" : "Company position"}</h2><p className="muted">Local cash uses each entity’s functional currency; headroom and forecast shortfall below use USD.{scope === "mnc" ? " Group totals are consolidated reporting figures. Cash pooling, intercompany funding and cross-border transfers require separate legal, tax and human approvals. A group surplus can hide an entity shortage." : " One domestic entity is shown, including its foreign-currency bank balances."}</p><div className="table-scroll"><table><thead><tr><th>Entity</th><th>Country</th><th>Available local cash</th><th>Headroom · USD</th><th>Forecast shortfall · USD</th></tr></thead><tbody>{positions.entities.map(entity => <tr key={entity.id}><td>{entity.name}</td><td>{entity.country}</td><td>{entity.functionalCurrency} {amount(entity.deployableLocal)}</td><td>{money(entity.headroom)}</td><td>{money(entity.maximumShortfall)}</td></tr>)}</tbody></table></div></article>
      <article className="panel"><h2>Hedge position</h2><p className="muted">Positive exposure means net receipts; negative means net payments. SELL hedges are negative and BUY hedges positive. Open invoices beyond the forecast horizon remain in this exposure view. This measures group exposure against USD; it does not replace each entity’s functional-currency hedging policy.</p><div className="table-scroll"><table><thead><tr><th>Currency</th><th>Open exposure</th><th>Existing hedge</th><th>Residual</th><th>Coverage</th><th>Review status</th></tr></thead><tbody>{positions.hedges.map(row => <tr key={row.currency}><td>{row.currency}</td><td>{amount(row.underlying)}</td><td>{amount(row.hedge)}</td><td>{amount(row.residual)}</td><td>{row.ratio === null ? "No exposure" : `${row.ratio}%`}</td><td>{row.status.toLowerCase().replaceAll("-", " ")}{row.wrongDirection ? " · direction mismatch" : ""}</td></tr>)}</tbody></table></div></article>
      <article className="panel"><h2>Updated 13-week cash outlook</h2><div className="table-scroll"><table><thead><tr><th>Week</th><th>Receipts · USD</th><th>Payments · USD</th><th>Closing cash · USD</th><th>Shortfall · USD</th></tr></thead><tbody>{positions.forecast.points.map(point => <tr key={point.week}><td>{point.week}</td><td>{money(point.inflows)}</td><td>{money(point.outflows)}</td><td>{money(point.closing)}</td><td>{money(point.shortfall)}</td></tr>)}</tbody></table></div><p className="muted">Weekly closing cash can hide intraday shortages. Forecast ending cash: {money(positions.forecast.ending)}.</p></article>
      <article className="panel"><h2>Dummy event history</h2><p className="muted">Each successful refresh replaces all position cards together. Matched settlements remove the open invoice to avoid counting the same cash twice.</p>{snapshot.history.length ? <div className="table-scroll"><table><thead><tr><th>Cycle</th><th>Source</th><th>Update</th><th>Outcome</th><th>Check</th></tr></thead><tbody>{snapshot.history.map(row => <tr key={row.cycle}><td>{row.cycle}</td><td>{row.source}</td><td>{row.title}</td><td>{row.outcome.toLowerCase()}</td><td>{row.reason}</td></tr>)}</tbody></table></div> : <p>No incoming events yet. The original dummy position is loaded.</p>}</article>
    </>}
  </section>;
}
