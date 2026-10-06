"use client";
import { useEffect, useState } from "react";

type RecordData = Record<string, unknown>;
export function CompanyAccess() {
  const [session, setSession] = useState<RecordData>({});
  const [failed, setFailed] = useState(false);
  useEffect(() => { setFailed(new URLSearchParams(window.location.search).get("signin") === "failed"); fetch("/api/auth/session", { cache: "no-store" }).then(r => r.json()).then(setSession).catch(() => setSession({ error: "Sign-in service unavailable" })); }, []);
  if (session.authenticated) return <div className="company-access"><span>{String(session.username)} · {String(session.role).replaceAll("_", " ")}</span><button className="button secondary" onClick={async () => { await fetch("/api/auth/logout", { method: "POST" }); window.location.reload(); }}>Sign out</button></div>;
  return <div className="company-access">{failed && <span role="status">Sign-in failed; verify your account access.</span>}{session.loginAvailable ? <a className="button secondary" href="/api/auth/login">Company sign-in</a> : <span className="muted">Company sign-in awaiting setup</span>}</div>;
}

export default function ReleaseWorkspace({ recordedDemo }: { recordedDemo: boolean }) {
  const [id, setId] = useState("");
  const [release, setRelease] = useState<RecordData | null>(null);
  const [events, setEvents] = useState<unknown[]>([]);
  const [session, setSession] = useState<RecordData>({});
  const [action, setAction] = useState("evidence");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [documentHash, setDocumentHash] = useState("");
  useEffect(() => { fetch("/api/auth/session", { cache: "no-store" }).then(r => r.json()).then(setSession).catch(() => setMessage("Company sign-in service unavailable.")); }, []);
  async function call(operation: string, body?: RecordData, selected = id) {
    const response = await fetch(`/api/workflow?action=${operation}&release=${encodeURIComponent(selected)}`, { method: body ? "POST" : "GET", headers: body ? { "Content-Type": "application/json" } : undefined, body: body ? JSON.stringify(body) : undefined, cache: "no-store" });
    const value = await response.json();
    if (!response.ok) throw new Error(value.error ?? "Request failed");
    return value;
  }
  async function load(selected = id) {
    const [status, history] = await Promise.all([call("status", undefined, selected), call("events", undefined, selected)]);
    setRelease(status); setEvents(history);
  }
  const role = String(session.role ?? "");
  const gates = (release?.required_gates ?? {}) as Record<string, string>;
  const editable = !recordedDemo && Boolean(session.authenticated);
  const signoffRoles = release?.required_signoff_roles as string[] | undefined;
  const can = action === "create" ? role === "GROUP_TREASURER" : action === "observation" ? ["TREASURY_ANALYST", "INTEGRATION_OWNER"].includes(role) : action === "signoff" ? Boolean(signoffRoles?.includes(role)) : action === "transition" ? ["GROUP_TREASURER", "OPERATIONS_MANAGER"].includes(role) : Object.values(gates).includes(role);
  return <article className="panel"><h2>Release evidence & decisions</h2><p className="muted">Save review records against a named release. Roles come from your company account. Evidence changes invalidate earlier sign-offs. Documents stay with you; only their fingerprint and reference are saved.</p>
    {!editable && <div className="inline-error">{recordedDemo ? "The recorded demonstration cannot save or approve records. Connect the hosted backend and company sign-in first." : "Company sign-in is required to use this workspace."}</div>}
    <form className="workflow-form" onSubmit={async e => { e.preventDefault(); setBusy(true); setMessage(""); try { await load(); } catch (error) { setRelease(null); setEvents([]); setMessage((error as Error).message); } finally { setBusy(false); } }}><label>Release number<input required inputMode="numeric" pattern="[1-9][0-9]*" value={id} onChange={e => { setId(e.target.value); setRelease(null); setEvents([]); }} /></label><button className="button secondary" disabled={!editable || busy}>Review release</button></form>
    {release && <><div className="detail-grid"><div><dt>State</dt><dd>{String(release.state)}</dd></div><div><dt>Readiness</dt><dd>{String(release.status)}</dd></div><div><dt>Evidence fingerprint</dt><dd>{String(release.evidence_digest)}</dd></div></div><ul className="bullet-list">{(release.blockers as string[] ?? []).map(b => <li key={b}>{b}</li>)}</ul><details><summary>Audit trail · {events.length} records</summary><div className="table-scroll"><table><thead><tr><th>Action</th><th>Person</th><th>Reason</th></tr></thead><tbody>{events.map((event, i) => { const row = event as RecordData; return <tr key={i}><td>{String(row.action)}</td><td>{String(row.actor)}</td><td>{String(row.reason)}</td></tr>; })}</tbody></table></div></details></>}
    <label className="workflow-label">Task<select value={action} onChange={e => { setAction(e.target.value); setMessage(""); }}><option value="create">Register a release candidate</option><option value="evidence">Record review evidence</option><option value="observation">Record a parallel-run comparison</option><option value="signoff">Submit your sign-off</option><option value="transition">Record a release decision</option></select></label>
    <form key={action} className="workflow-form" onSubmit={async e => {
      e.preventDefault(); setBusy(true); setMessage("");
      try {
        const fields = Object.fromEntries(new FormData(e.currentTarget)) as RecordData;
        if (action === "evidence") { fields.details = JSON.parse(String(fields.details || "{}")); fields.expires_at = new Date(String(fields.expires_at)).toISOString(); }
        if (action === "signoff") fields.evidence_digest = release?.evidence_digest;
        const result = await call(action, fields);
        const selected = action === "create" ? String(result.id) : id;
        setId(selected); await load(selected); setMessage("Record saved. Review the refreshed status and audit trail.");
      } catch (error) { setMessage((error as Error).message); } finally { setBusy(false); }
    }}>
      {action === "create" ? <><Field name="name" title="Release name" /><Field name="artifact_sha256" title="Candidate artifact SHA-256" hash /><Field name="previous_artifact_sha256" title="Rollback artifact SHA-256" hash /></> : action === "evidence" ? <><label>Review gate<select name="gate" required>{Object.entries(gates).filter(([, owner]) => owner === role).map(([gate]) => <option key={gate}>{gate}</option>)}</select></label><Kind /><label>Result<select name="result"><option>FAIL</option><option>PASS</option></select></label><Field name="reference" title="Evidence location or reference" /><Field name="scope" title="Scope (entity / accounts / systems)" /><label>Valid until<input name="expires_at" type="datetime-local" required /></label><label>Fingerprint a document<input type="file" onChange={async e => { const file = e.target.files?.[0]; if (!file) return; if (file.size > 10485760) { setMessage("Choose a document under 10 MB."); return; } const hash = await crypto.subtle.digest("SHA-256", await file.arrayBuffer()); setDocumentHash(Array.from(new Uint8Array(hash), x => x.toString(16).padStart(2, "0")).join("")); }} /></label><label>Document SHA-256<input name="document_sha256" required pattern="[a-f0-9]{64}" value={documentHash} onChange={e => setDocumentHash(e.target.value)} /></label><label className="wide">Gate-specific supporting details (JSON)<textarea name="details" defaultValue="{}" rows={4} required /></label></> : action === "observation" ? <><Field name="day" title="Observation date" type="date" /><label>Measure<select name="metric">{["CASH", "FORECAST", "FX", "LIQUIDITY", "PAYMENTS", "RISK"].map(m => <option key={m}>{m}</option>)}</select></label><Kind /><Field name="scope" title="Scope" /><Field name="incumbent" title="Incumbent system value" /><Field name="platform" title="Treasury platform value" /><Field name="document_sha256" title="Comparison evidence SHA-256" hash /></> : action === "signoff" ? <><label>Decision<select name="decision"><option>REJECT</option><option>APPROVE</option></select></label><Field name="reason" title="Review reason" /></> : <><label>Decision<select name="action"><option>START_PARALLEL</option><option>HALT</option><option>ROLLBACK</option><option>GO_LIVE</option></select></label><Field name="reason" title="Decision reason" /><p className="muted wide">A governance decision does not deploy software, restore a database or send payments. The operator runbook remains required.</p></>}
      <button className="button secondary" disabled={!editable || !can || busy || action !== "create" && !release}>{busy ? "Saving…" : "Submit record"}</button>
    </form><p className="muted">{editable && !can ? "Your assigned role cannot submit this task." : "Every submission is checked again by the backend."}</p>{message && <p role="status" className="inline-error">{message}</p>}
  </article>;
}
function Field({ name, title, type = "text", hash = false }: { name: string; title: string; type?: string; hash?: boolean }) { return <label>{title}<input name={name} type={type} required maxLength={hash ? 64 : 2000} pattern={hash ? "[a-f0-9]{64}" : undefined} /></label>; }
function Kind() { return <label>Evidence source<select name="kind"><option>SYNTHETIC</option><option>REAL</option></select></label>; }
