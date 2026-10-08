"use client";

import { useEffect, useState } from "react";
import catalog from "../lib/endpoints.json";
import ReleaseWorkspace, { CompanyAccess } from "./ReleaseWorkspace";
import PlanningWorkspace from "./PlanningWorkspace";
import CompanyWorkspace from "./CompanyWorkspace";
import AutomaticUpdates from "./AutomaticUpdates";
import TreasuryPet from "./TreasuryPet";

type Data = Record<string, unknown>;
type Result = { data?: unknown; error?: string };
type Pilot = { as_of: string; scenarios: { case: string; forecast: Data; opening_liquidity: Data }[] };
const nav = [["start", "Start here", "⌂"], ["company", "Company setup", "▦"], ["automatic", "Automatic updates", "↻"], ["overview", "Dashboard", "◈"], ["forecast", "Cash forecast", "↗"], ["energy", "Energy pilot", "◉"], ["planning", "Cash planning", "↔"], ["risk", "Risks", "◇"], ["funding", "Funding & entities", "⇄"], ["integrations", "Data connections", "▤"], ["governance", "Approvals & readiness", "✓"], ["agents", "AI teams", "✦"], ["analytics", "Analysis library", "▥"]];
const workspaces: Record<string, string[]> = {
  overview: ["getLiquidity", "getForecast", "getTreasurySummary", "getAgentRuntime"],
  forecast: ["getForecast", "getStressSummary", "getForecastAccuracy", "getForecastDrivers"],
  risk: ["getDerivativeRisk", "getHedgeCoverage", "getInterestRateRisk", "getCounterpartyRisk"],
  funding: ["getCashMobility", "getFundingConcentration", "getCrossBorderGraph", "getLiquiditySurvival"],
  integrations: ["getProductionPhase1Status", "getProductionPhase1ParallelReadiness", "getSourceAuthorities"],
  governance: ["productionGate", "getEnterpriseSecurityPosture", "getOperationalResilience"],
  agents: ["getAgentRuntime", "getTreasurySummary"],
};
const descriptions: Record<string, string> = {
  automatic: "Watch a dummy feed recalculate cash, hedges and risk checks automatically.",
  company: "Set up your business, entities and team before connecting real data.",
  start: "Choose a task. We’ll guide you through the next steps.",
  overview: "Your cash position, upcoming pressure and decisions that need attention.",
  forecast: "Follow cash over the next 13 weeks and compare stressed outcomes.",
  energy: "Fictional oil-business cash flows, tested through deterministic treasury engines.",
  risk: "Monitor FX hedges, derivatives, interest rates and counterparty exposure.",
  funding: "Understand where cash sits and the constraints on moving or funding it.",
  integrations: "Track source quality, reconciliation and shadow-to-active promotion.",
  governance: "External evidence and human sign-offs determine whether execution can begin.",
  agents: "Five reasoning teams support decisions. Deterministic engines calculate the numbers.",
  analytics: "Explore specialist capabilities one analysis at a time.",
  planning: "Check a cash-flow file and compare your own planning scenarios privately.",
};
function obj(v: unknown): Data { return v && typeof v === "object" && !Array.isArray(v) ? v as Data : {}; }
function label(v: string) { return v.replace(/^get/, "").replace(/_/g, " ").replace(/([a-z])([A-Z])/g, "$1 $2").replace(/\b\w/g, x => x.toUpperCase()); }
function money(v: unknown, currency = "USD") {
  return v === undefined || v === null || !Number.isFinite(Number(v)) ? "—" : new Intl.NumberFormat("en-US", { style: "currency", currency, notation: "compact", maximumFractionDigits: 2 }).format(Number(v));
}
function scalar(v: unknown) {
  if (v == null) return "Not available";
  if (typeof v === "boolean") return v ? "Yes" : "No";
  if (typeof v === "string" && /^-?\d+\.\d+$/.test(v)) return new Intl.NumberFormat("en-US", { maximumFractionDigits: 4 }).format(Number(v));
  return String(v);
}
function Badge({ children, tone = "neutral" }: { children: React.ReactNode; tone?: string }) { return <span className={`badge ${tone}`}>{children}</span>; }
function Details({ value, depth = 0 }: { value: unknown; depth?: number }) {
  if (Array.isArray(value)) {
    if (!value.length) return <p className="muted">No records reported.</p>;
    if (value.every(x => typeof x !== "object" || x === null)) return <ul className="bullet-list">{value.map((x, i) => <li key={i}>{scalar(x)}</li>)}</ul>;
    const rows = value.map(obj);
    const keys = rows[0].week !== undefined
      ? ["week", "week_start", "expected_inflows", "expected_outflows", "closing_cash", "minimum_buffer", "liquidity_headroom", "shortfall"]
      : [...new Set(rows.flatMap(Object.keys))].filter(k => rows.some(r => typeof r[k] !== "object")).slice(0, 8);
    return <div className="table-scroll"><table><thead><tr>{keys.map(k => <th key={k}>{label(k)}</th>)}</tr></thead><tbody>{rows.map((r, i) => <tr key={i}>{keys.map(k => <td key={k}>{typeof r[k] === "object" && r[k] !== null ? "Detailed record" : scalar(r[k])}</td>)}</tr>)}</tbody></table></div>;
  }
  if (value && typeof value === "object") {
    const pairs = Object.entries(obj(value));
    return <><dl className="detail-grid">{pairs.filter(([, v]) => typeof v !== "object" || v === null).map(([k, v]) => <div key={k}><dt>{label(k)}</dt><dd>{scalar(v)}</dd></div>)}</dl>{pairs.filter(([, v]) => v !== null && typeof v === "object").map(([k, v]) => <details key={k} open={depth === 0 && ["warnings", "blockers"].includes(k)}><summary>{label(k)}{Array.isArray(v) ? ` · ${v.length}` : ""}</summary><Details value={v} depth={depth + 1} /></details>)}</>;
  }
  return <p>{scalar(value)}</p>;
}
function EntityTable({ value, currency }: { value: unknown; currency: string }) {
  const rows = Array.isArray(value) ? value.map(obj) : [];
  if (!rows.length) return <p className="muted">Entity balances are not available yet.</p>;
  return <div className="table-scroll"><table><thead><tr><th>Legal entity</th><th>Currency</th><th>Deployable cash</th><th>Cash buffer</th><th>Headroom</th></tr></thead><tbody>{rows.map((r, i) => <tr key={i}><td>{scalar(r.entity_name)}</td><td>{scalar(r.local_currency)}</td><td>{money(r.deployable_cash_reporting, currency)}</td><td>{money(r.minimum_cash_reporting, currency)}</td><td className={Number(r.liquidity_headroom_reporting) < 0 ? "negative" : ""}>{money(r.liquidity_headroom_reporting, currency)}</td></tr>)}</tbody></table></div>;
}
function Chart({ forecast }: { forecast: Data }) {
  const points = Array.isArray(forecast.points) ? forecast.points.map(obj) : [];
  if (!points.length) return <p className="muted">Forecast not available yet.</p>;
  const max = Math.max(...points.map(p => Math.abs(Number(p.closing_cash))), ...points.map(p => Number(p.minimum_buffer)), 1);
  return <div className="cash-chart" role="img" aria-label="Weekly closing cash and minimum buffer"><div className="chart-legend"><span><i /> Closing cash</span><span><i className="buffer-dot" /> Minimum buffer</span></div><div className="bars">{points.map(p => <div className="chart-column" key={String(p.week)}><div className="bar-track"><div className={`bar ${Number(p.shortfall) > 0 ? "danger-bar" : ""}`} style={{ height: `${Math.max(2, Math.abs(Number(p.closing_cash)) / max * 100)}%` }} /><div className="buffer-mark" style={{ bottom: `${Number(p.minimum_buffer) / max * 100}%` }} /></div><span>{money(p.closing_cash)}</span><small>W{String(p.week)}</small></div>)}</div></div>;
}
function Metrics({ items }: { items: [string, unknown, string][] }) { return <section className="metric-grid">{items.map(([title, value, note]) => <article className="metric-card" key={title}><span>{title}</span><strong>{money(value)}</strong><small>{note}</small></article>)}</section>; }

export default function Dashboard({ pilot, recordedDemo }: { pilot: Pilot; recordedDemo: boolean }) {
  const [view, setView] = useState("start");
  const [automaticOpened, setAutomaticOpened] = useState(false);
  const [companyOpened, setCompanyOpened] = useState(false);
  useEffect(() => { if (view === "company") setCompanyOpened(true); }, [view]);
  useEffect(() => { if (view === "automatic") setAutomaticOpened(true); }, [view]);
  const [analysis, setAnalysis] = useState("getTreasuryRiskRadar");
  const [pilotCase, setPilotCase] = useState("BASE");
  const [results, setResults] = useState<Record<string, Result>>({});
  const [loading, setLoading] = useState(false);
  const [revision, setRevision] = useState(0);
  const [refreshed, setRefreshed] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const signature = (view === "analytics" ? [analysis] : workspaces[view] ?? []).join(",");
  useEffect(() => {
    const controller = new AbortController();
    const keys = signature ? signature.split(",") : [];
    setLoading(keys.length > 0); setResults({});
    const tasks = keys.map(async key => {
      let result: Result;
      try {
        const response = await fetch(`/api/treasury?key=${encodeURIComponent(key)}`, { signal: controller.signal, cache: "no-store" });
        const body = await response.json();
        result = response.ok ? { data: body } : { error: body.error ?? "Analysis unavailable. Retry this workspace." };
      } catch {
        if (controller.signal.aborted) return;
        result = { error: "Connection interrupted. Retry this workspace." };
      }
      if (!controller.signal.aborted) setResults(previous => ({ ...previous, [key]: result }));
    });
    Promise.allSettled(tasks).then(() => { if (!controller.signal.aborted) { setLoading(false); setRefreshed(new Date().toLocaleTimeString()); } });
    return () => controller.abort();
  }, [signature, revision]);
  const keys = signature ? signature.split(",") : [];
  const liq = obj(results.getLiquidity?.data), forecast = obj(results.getForecast?.data), summary = obj(results.getTreasurySummary?.data);
  const findings = Array.isArray(summary.findings) ? summary.findings.map(obj) : [];
  const selected = pilot.scenarios.find(s => s.case === pilotCase) ?? pilot.scenarios[0];
  const title = nav.find(n => n[0] === view)?.[1] ?? "Overview";
  const labels: Record<string, { label: string }> = catalog;
  function navButton([id, text, icon]: string[]) { return <button key={id} aria-current={view === id ? "page" : undefined} className={view === id ? "nav-item active" : "nav-item"} onClick={() => setView(id)}><span aria-hidden="true">{icon}</span>{text}{id === "energy" && <small>DEMO</small>}</button>; }
  function panel(key: string) {
    const result = results[key];
    return <article className="panel" key={key}><div className="panel-heading"><h2>{key === "productionGate" ? "Controlled go-live gate" : labels[key]?.label ?? label(key)}</h2><Badge>{result?.error ? "Unavailable" : result?.data ? "Loaded" : "Loading"}</Badge></div>{result?.error ? <div className="empty-state" role="alert"><strong>We couldn’t load this analysis</strong><p>{result.error}</p><button className="text-button" onClick={() => setRevision(r => r + 1)}>Retry workspace →</button></div> : result?.data ? <Details value={result.data} /> : <div className="skeleton" aria-label="Loading analysis" />}</article>;
  }
  return <div className="app-shell"><a className="skip-link" href="#workspace">Skip to workspace</a>
    <aside className="sidebar"><a className="brand" href="/"><span className="brand-mark">T</span><span>Global Treasury<small>INTELLIGENCE PLATFORM</small></span></a><div className="workspace-label">TREASURY WORKSPACE</div><nav aria-label="Treasury workspaces">{nav.filter(([id]) => ["start", "company", "automatic", "overview", "planning", "risk", "integrations", "governance"].includes(id)).map(navButton)}<details className="advanced-nav" open={["forecast", "energy", "funding", "agents", "analytics"].includes(view) ? true : undefined}><summary>More reports</summary>{nav.filter(([id]) => ["forecast", "energy", "funding", "agents", "analytics"].includes(id)).map(navButton)}</details></nav><div className="sidebar-bottom"><div className="system-dot" /> Deterministic engines<small>AI supports. Humans decide.</small><div className="profile"><span>TP</span><div>Company workspace<small>{recordedDemo ? "Recorded demonstration" : "Dedicated deployment"}</small></div></div></div></aside>
    <div className="workspace"><header className="topbar"><div className="breadcrumb">Workspace <span>/</span> <strong>{title}</strong></div><div className="topbar-actions"><Badge tone="warning">{recordedDemo ? "Synthetic data" : "Governed sources"}</Badge><CompanyAccess /></div></header><main id="workspace">
      <div className="page-heading"><div><p className="eyebrow">GLOBAL TREASURY AI</p><h1>{view === "overview" ? "Treasury at a glance" : title}</h1><p className="muted">{descriptions[view]}</p></div>{!["start", "company", "automatic", "planning"].includes(view) && <button className="button secondary" disabled={loading} onClick={() => setRevision(r => r + 1)}>{loading ? "Refreshing…" : "↻ Refresh workspace"}</button>}</div>
      {!["start", "company", "automatic", "planning"].includes(view) && <div className="demo-notice"><span>◈</span><div><strong>{recordedDemo ? "Recorded demonstration · execution disabled" : "Connected calculation service · production gates apply"}</strong><p>{recordedDemo ? "Analyses show recorded synthetic engine outputs, not current calculations or live feeds. " : "Results follow the backend source policies. "}Energy pilot uses a separate fictional oil-business dataset. Real integrations require verified source evidence.</p></div><button onClick={() => setView("governance")}>View readiness →</button></div>}
      {view === "start" && <section className="start-workspace"><div className="start-intro"><p className="eyebrow">YOUR FIRST STEP</p><h2>What would you like to do?</h2><p>Set up your company, plan its cash flows, and review the controls needed before real use. Specialist reports cover funding, currencies and other treasury risks.</p></div><div className="start-cards">
        <article className="panel start-card"><span className="start-icon" aria-hidden="true">◉</span><span className="badge">Company onboarding</span><h3>Set up my company</h3><p>Register your business and legal entities, then review data connections and staff roles.</p><button className="button secondary" onClick={() => setView("company")}>Open company setup →</button><small>{recordedDemo ? "Try editable dummy setup · session only" : "Company sign-in required to save records"}</small></article>
        <article className="panel start-card"><span className="start-icon" aria-hidden="true">↗</span><span className="badge">Private planning</span><h3>Plan my cash flows</h3><p>Upload a CSV, check the records, enter your assumptions and try a what-if.</p><button className="button secondary" onClick={() => setView("planning")}>Start cash planning →</button><small>Files stay in this browser session · CSV / TSV</small></article>
        <article className="panel start-card"><span className="start-icon" aria-hidden="true">✓</span><span className="badge warning">Evidence required</span><h3>Review production readiness</h3><p>Understand missing evidence, sign-offs and the controls needed before execution.</p><button className="button secondary" onClick={() => setView("governance")}>Review readiness →</button><small>Real integrations and human approvals required</small></article>
      </div><div className="start-help"><strong>Try automatic updates</strong><p>Watch a fictional company’s bank, invoice and market events update its position. <button className="text-button" onClick={() => setView("automatic")}>open automatic updates →</button> Rodger explains each screen. You can also <button className="text-button" onClick={() => setView("overview")}>open the cash dashboard →</button></p></div><p className="muted">{recordedDemo ? "The public dashboard uses recorded fictional data. Cash planning calculates fresh results from your chosen dataset and assumptions." : "Connected reports follow backend source policies. Cash planning is a separate local sandbox."} Planning does not approve payments or clear production gates.</p></section>}
      <div hidden={view !== "automatic"}>{(automaticOpened || view === "automatic") && <AutomaticUpdates active={view === "automatic"} />}</div>
      <div hidden={view !== "company"}>{(companyOpened || view === "company") && <CompanyWorkspace recordedDemo={recordedDemo} navigate={setView} />}</div>
      <div hidden={view !== "planning"}><PlanningWorkspace /></div>
      {view === "overview" && <><Metrics items={[["Deployable cash", liq.deployable_cash, "After restrictions and commitments"], ["Liquidity headroom", liq.liquidity_headroom, "Cash + credit less minimum buffer"], ["13-week ending cash", forecast.ending_cash, "Base forecast · reporting currency USD"], ["Cash buffer", liq.minimum_cash, "Configured minimum cash policy"]]} />{(results.getLiquidity?.error || results.getForecast?.error) && <div className="inline-error" role="alert">Cash figures are unavailable. Dashes are missing data, not zero. Refresh to retry.</div>}
        <section className="overview-grid"><article className="panel"><div className="panel-heading"><div><p className="eyebrow">CASH OUTLOOK</p><h2>13-week liquidity forecast</h2></div><button className="text-button" onClick={() => setView("forecast")}>Explore →</button></div><Chart forecast={forecast} /></article><article className="panel"><p className="eyebrow">NEXT STEPS</p><h2>Focus for your team</h2><div className="action-row"><span className="action-number">01</span><div><strong>Review interim funding gaps</strong><p>Combined energy stress creates a {money(pilot.scenarios.find(s => s.case === "COMBINED")?.forecast.maximum_shortfall)} buffer shortfall.</p><button className="text-button" onClick={() => setView("energy")}>Open energy pilot →</button></div></div><div className="action-row"><span className="action-number">02</span><div><strong>Complete external validation</strong><p>Real evidence, independent reviews and named approvers are still required.</p><button className="text-button" onClick={() => setView("governance")}>Review go-live blockers →</button></div></div></article></section>
        <section className="overview-grid"><article className="panel"><div className="panel-heading"><h2>Cash by legal entity</h2><Badge>USD equivalent</Badge></div><EntityTable value={liq.entities} currency={String(liq.reporting_currency ?? "USD")} /></article><article className="panel"><div className="panel-heading"><h2>Risk & control signals</h2><Badge tone="warning">{results.getTreasurySummary?.data ? `${findings.length} signals` : results.getTreasurySummary?.error ? "Unavailable" : "Loading"}</Badge></div>{results.getTreasurySummary?.error ? <p role="alert">{results.getTreasurySummary.error}</p> : !results.getTreasurySummary ? <div className="skeleton" /> : findings.length ? findings.slice(0, 5).map((f, i) => <div className="finding" key={i}><Badge tone={["HIGH", "CRITICAL"].includes(String(f.severity)) ? "danger" : "warning"}>{scalar(f.severity)}</Badge><strong>{scalar(f.title)}</strong><p>{scalar(f.message)}</p></div>) : <p className="muted">No signals reported.</p>}</article></section></>}
      {view === "forecast" && <><article className="panel"><div className="panel-heading"><h2>Base cash outlook</h2><Badge>13 weeks</Badge></div><Chart forecast={forecast} />{results.getForecast?.error && <p role="alert">{results.getForecast.error}</p>}</article>{keys.map(panel)}</>}
      {view === "energy" && <><section className="pilot-intro"><div><p className="eyebrow">FICTIONAL ENERGY TRADING GROUP</p><h2>Crude purchases. Product receipts. Cash timing.</h2><p>UK + Singapore · USD / GBP / SGD · assumed SAP boundary</p></div><Badge tone="warning">Synthetic rehearsal · {pilot.as_of}</Badge></section><div className="scenario-controls" role="group" aria-label="Energy stress scenarios">{pilot.scenarios.map(s => <button key={s.case} aria-pressed={pilotCase === s.case} className={pilotCase === s.case ? "scenario-button selected" : "scenario-button"} onClick={() => setPilotCase(s.case)}>{label(s.case)}</button>)}</div><Metrics items={[["Opening cash", selected.opening_liquidity.deployable_cash, "Assumed FX rates"], ["Ending cash", selected.forecast.ending_cash, "13-week forecast"], ["Maximum buffer shortfall", selected.forecast.maximum_shortfall, "Minimum group buffer: $15m"], ["Cash buffer", selected.opening_liquidity.minimum_cash, selected.forecast.first_buffer_breach_week ? `First breach: week ${selected.forecast.first_buffer_breach_week}` : "No weekly buffer breach"]]} /><article className="panel"><h2>{label(pilotCase)} cash outlook</h2><Chart forecast={selected.forecast} /><Details value={selected.forecast.points} /></article><div className="demo-notice"><span>!</span><div><strong>Group cash does not guarantee local availability</strong><p>Singapore opens $0.2m below its entity buffer. Transfers require legal, tax and operational review. Weekly forecasts do not establish intraday solvency.</p></div></div><p className="muted">All five cases passed independent cash arithmetic. The incomplete synthetic release denied execution. No commodity valuation or real-provider certification is claimed.</p></>}
      {view === "governance" && <ReleaseWorkspace recordedDemo={recordedDemo} />}
      {view === "analytics" && <><article className="panel library-picker"><label htmlFor="analysis-search">Find a specialist analysis</label><input id="analysis-search" type="search" value={query} onChange={e => setQuery(e.target.value)} placeholder="Search liquidity, collateral, forecasts…" /><label htmlFor="analysis-select">Analysis</label><select id="analysis-select" value={analysis} onChange={e => setAnalysis(e.target.value)}>{Object.entries(catalog).filter(([key, item]) => key === analysis || item.label.toLowerCase().includes(query.toLowerCase())).map(([key, item]) => <option key={key} value={key}>{item.label}</option>)}</select></article>{panel(analysis)}</>}
      {["risk", "funding", "integrations", "governance", "agents"].includes(view) && <>{view === "governance" && <div className="readiness-banner"><Badge tone="danger">Live execution blocked</Badge><h2>Evidence first. Controlled go-live.</h2><p>Service availability is separate from release approval. Real certifications, independent validation, security, recovery, UAT and human sign-offs remain mandatory.</p></div>}{view === "agents" && <div className="agent-grid">{["Liquidity & Funding", "Market & Derivatives Risk", "Global Treasury & Tax", "Risk, Controls & Model Governance", "Treasury Orchestrator & Decision"].map((name, i) => <article className="agent-card" key={name}><span>0{i + 1}</span><h3>{name}</h3><Badge>Decision support</Badge></article>)}</div>}{keys.map(panel)}</>}
      <footer className="workspace-footer"><span>Deterministic calculations · Human approval boundaries · {recordedDemo ? "Synthetic reference data" : "Governed backend sources"}</span><span aria-live="polite">{loading ? "Loading selected workspace…" : refreshed ? `${recordedDemo ? "Snapshot loaded" : "Last refresh"} ${refreshed}` : ""}</span></footer>
    </main></div>
    <TreasuryPet view={view} navigate={setView} recordedDemo={recordedDemo} />
  </div>;
}
