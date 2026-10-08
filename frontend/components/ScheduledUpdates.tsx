"use client";
import { useEffect, useState } from "react";
import { fictionalSchedules, validateSchedule, type UpdateSchedule, type UpdateSchedules } from "../lib/scheduled-updates";

function ScheduleRow({ row, editable, busy, save }: { row: UpdateSchedule; editable: boolean; busy: boolean; save: (row: UpdateSchedule, interval: number, stale: number, enabled: boolean) => Promise<void> }) {
  const [interval, setInterval] = useState(String(row.interval_minutes)), [stale, setStale] = useState(String(row.stale_after_minutes)), [enabled, setEnabled] = useState(row.enabled);
  return <article className="panel"><h3>{row.connector_name}</h3><p>{row.freshness === "MISSING" ? "No accepted update recorded." : row.freshness === "STALE" ? "The last accepted update is old. Review before relying on it." : row.freshness === "INVALID_TIMESTAMP" ? "The update timestamp needs review." : "A recent accepted update is recorded. Coverage still needs review."}</p>
    <p>Last accepted event: {row.last_success_at ? `${row.last_success_at} UTC` : "Unavailable"}. Last collection attempt: {row.last_attempt_status.replaceAll("_", " ").toLowerCase()}.</p><p>{row.last_attempt_reason}</p>
    <p>Source permission: {row.authority.length ? row.authority.map(a => `${a.domain}: ${a.mode}`).join(", ") : "Unassigned — source review required"}. Saving a schedule cannot approve a source.</p>
    <form className="company-form" onSubmit={event => { event.preventDefault(); void save(row, Number(interval), Number(stale), enabled); }}><label>Check for updates every (minutes)<input type="number" min="5" max="10080" step="1" value={interval} disabled={!editable || busy} onChange={event => setInterval(event.target.value)} /></label>
      <label>Warn me when data is older than (minutes)<input type="number" min="5" max="20160" step="1" value={stale} disabled={!editable || busy} onChange={event => setStale(event.target.value)} /></label>
      <label><input type="checkbox" checked={enabled} disabled={!editable || busy || row.connector_status !== "ACTIVE"} onChange={event => setEnabled(event.target.checked)} /> Request scheduled collection when a worker is connected</label><button className="button secondary" disabled={!editable || busy}>Save update settings</button></form>
    {row.next_due_at && <p>Next requested check: {row.next_due_at} UTC{row.due ? " — due; worker required" : ""}.</p>}</article>;
}

export default function ScheduledUpdates({ recordedDemo }: { recordedDemo: boolean }) {
  const [data, setData] = useState<UpdateSchedules | null>(recordedDemo ? fictionalSchedules() : null), [message, setMessage] = useState(""), [busy, setBusy] = useState(false);
  async function request(body?: object) {
    const response = await fetch("/api/scheduled-updates", { method: body ? "PUT" : "GET", headers: body ? { "Content-Type": "application/json" } : undefined, body: body ? JSON.stringify(body) : undefined, cache: "no-store", signal: AbortSignal.timeout(45000) });
    const value = await response.json(); if (!response.ok) throw new Error(value.error ?? "Update settings are unavailable. Connect the company backend and sign in."); return value as UpdateSchedules;
  }
  useEffect(() => { if (recordedDemo) return; let cancelled = false; request().then(value => { if (!cancelled) setData(value); }).catch(error => { if (!cancelled) setMessage(error.message); }); return () => { cancelled = true; }; }, [recordedDemo]);
  async function reload() {
    setBusy(true); setMessage("");
    try { setData(await request()); setMessage("Saved settings and source status reloaded."); }
    catch (error) { setMessage((error as Error).message); }
    finally { setBusy(false); }
  }
  async function save(row: UpdateSchedule, interval: number, stale: number, enabled: boolean) {
    setMessage(""); setBusy(true);
    try { validateSchedule(interval, stale); const body = { connector_id: row.connector_id, interval_minutes: interval, stale_after_minutes: stale, enabled, expected_version: row.version };
      if (recordedDemo) { setData(current => current && ({ ...current, schedules: current.schedules.map(item => item.connector_id === row.connector_id ? { ...item, interval_minutes: interval, stale_after_minutes: stale, enabled, version: item.version + 1 } : item) })); setMessage("Example settings saved for this visit. No real updates have been scheduled."); }
      else { setData(await request(body)); setMessage("Settings saved. Collection remains blocked until an approved worker is configured."); }
    } catch (error) { setMessage((error as Error).message); } finally { setBusy(false); }
  }
  return <section className="scheduled-workspace"><h2>Keep company data up to date</h2><p>One upload gives you a snapshot. New bills, receipts and prices need another upload or an approved connected feed.</p><p>{data?.worker_reason ?? "Connect the authenticated company backend to review update settings."}</p><p>No payment or hedge trade is sent by these settings.</p>{message && <p role="status">{message}</p>}
    {!recordedDemo && <button className="button secondary" disabled={busy} onClick={reload}>Reload update settings</button>}
    {data?.schedules.length === 0 && <p>No registered connectors yet. Your operator must register a reviewed data source first.</p>}{data?.schedules.map(row => <ScheduleRow key={`${row.connector_id}:${row.version}`} row={row} editable={data.can_edit} busy={busy} save={save} />)}{data && <p>{data.freshness_basis}</p>}</section>;
}
