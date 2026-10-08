"use client";
import { useEffect, useState } from "react";
import { countries, currencies, reviewerRoles, examplePreferences, validatePreferences, type Preferences, type PreferenceState } from "../lib/company-preferences";

const empty = (): Preferences => ({ countries: [], currencies: [], minimum_cash_usd: "0", reviewer_roles: [] });
const countryNames: Record<string, string> = { US: "United States", GB: "United Kingdom", IN: "India", DE: "Germany", FR: "France", SG: "Singapore", AE: "United Arab Emirates", HK: "Hong Kong", CN: "China", JP: "Japan", CH: "Switzerland", CA: "Canada", AU: "Australia", NL: "Netherlands", SA: "Saudi Arabia", BR: "Brazil", ZA: "South Africa" };
export default function CompanyPreferences({ recordedDemo }: { recordedDemo: boolean }) {
  const [value, setValue] = useState<Preferences>(empty);
  const [saved, setSaved] = useState<PreferenceState | null>(null);
  const [busy, setBusy] = useState(false), [message, setMessage] = useState("");
  async function request(body?: object) {
    const response = await fetch("/api/company-preferences", { method: body ? "PUT" : "GET", cache: "no-store", headers: body ? { "Content-Type": "application/json" } : undefined, body: body ? JSON.stringify(body) : undefined, signal: AbortSignal.timeout(45000) });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || "Company preference draft is unavailable.");
    return result as PreferenceState;
  }
  function apply(result: PreferenceState) {
    setSaved(result);
    setValue(result.draft ? validatePreferences(result.draft) : empty());
  }
  async function reload() {
    setBusy(true); setMessage("");
    try { apply(await request()); } catch (error) { setSaved(null); setMessage((error as Error).message); } finally { setBusy(false); }
  }
  useEffect(() => {
    let cancelled = false;
    setSaved(null); setValue(empty()); setMessage("");
    if (!recordedDemo) {
      setBusy(true);
      request().then(result => { if (!cancelled) apply(result); }).catch(error => { if (!cancelled) setMessage(error.message); }).finally(() => { if (!cancelled) setBusy(false); });
    } else setBusy(false);
    return () => { cancelled = true; };
  }, [recordedDemo]);
  const editable = !busy && (recordedDemo || Boolean(saved?.can_edit));
  function toggle(field: "countries" | "currencies" | "reviewer_roles", item: string) {
    setValue(previous => ({ ...previous, [field]: previous[field].includes(item) ? previous[field].filter(v => v !== item) : [...previous[field], item] }));
  }
  async function save() {
    try {
      const draft = validatePreferences(value);
      if (recordedDemo) {
        setSaved({ can_edit: true, status: "DRAFT_NOT_ACTIVATED", draft: { ...draft, version: (saved?.draft?.version || 0) + 1 } });
        setMessage("Dummy preferences saved for this session. They do not change calculations, staff access or approval rules.");
      } else {
        setBusy(true); apply(await request({ ...draft, expected_version: saved?.draft?.version || 0 }));
        setMessage("Preference draft saved for review. Treasury policies and account permissions remain controlled separately.");
      }
    } catch (error) { setMessage((error as Error).message); } finally { setBusy(false); }
  }
  return <article className="panel company-preferences">
    <p className="eyebrow">COMPANY PREFERENCES · DRAFT ONLY</p><h2>Describe how your business works</h2>
    <p>Select where you operate, currencies you use, money you would like to keep available and which existing roles should review your draft. These preferences do not activate policies or give anyone permissions.</p>
    <p className="muted">{recordedDemo ? "Fictional practice only. Reloading this page clears these preferences." : "Saved in your dedicated company backend. Only the Group Treasurer can change the draft."}</p>
    {recordedDemo ? <div className="button-row"><button className="button secondary" onClick={() => { setValue(examplePreferences()); setMessage("Fictional US company example loaded. Save it to keep it during this session."); }} disabled={busy}>Try fictional preferences</button><button className="button secondary" onClick={() => { setValue(empty()); setSaved(null); setMessage("Dummy preferences cleared."); }} disabled={busy}>Clear dummy preferences</button></div> : <button className="button secondary" onClick={reload} disabled={busy}>Reload saved preferences</button>}
    <fieldset disabled={!editable}><legend>Countries where you operate</legend><div className="button-row">{countries.map(item => <label key={item}><input type="checkbox" checked={value.countries.includes(item)} onChange={() => toggle("countries", item)} /> {countryNames[item]} ({item})</label>)}</div></fieldset>
    <fieldset disabled={!editable}><legend>Currencies you use</legend><div className="button-row">{currencies.map(item => <label key={item}><input type="checkbox" checked={value.currencies.includes(item)} onChange={() => toggle("currencies", item)} /> {item}</label>)}</div></fieldset>
    <label>Suggested minimum available money (USD)<input inputMode="decimal" value={value.minimum_cash_usd} disabled={!editable} onChange={event => setValue(previous => ({ ...previous, minimum_cash_usd: event.target.value }))} /></label>
    <p className="muted">This draft target applies to no calculation automatically. A group target does not guarantee money is available at every company.</p>
    <fieldset disabled={!editable}><legend>Suggested review roles</legend><div className="button-row">{reviewerRoles.map(item => <label key={item}><input type="checkbox" checked={value.reviewer_roles.includes(item)} onChange={() => toggle("reviewer_roles", item)} /> {item.replaceAll("_", " ").toLowerCase()}</label>)}</div></fieldset>
    <button className="button" onClick={save} disabled={!editable}>{busy ? "Saving…" : recordedDemo ? "Save dummy preferences" : "Save preference draft"}</button>
    {saved?.draft && <p>Saved draft version {saved.draft.version} · not activated</p>}{message && <p role="status">{message}</p>}
  </article>;
}
