"use client";
import { useEffect, useState } from "react";

type Profile = { company_name: string; industry: string; country_code: string; version: number };
type Entity = { id: number; name: string; country_code: string; functional_currency: string; status?: string; active?: boolean };
type Setup = { profile: Profile | null; reporting_currency: string; can_edit: boolean; registrations: Entity[]; entities: Entity[]; users: { display_name: string; role: string }[] };
const industries = ["MANUFACTURING", "ENERGY", "SERVICES", "RETAIL", "FINANCIAL_SERVICES", "OTHER"];
const label = (value: string) => value.replaceAll("_", " ").toLowerCase();

export default function CompanyWorkspace({ recordedDemo, navigate }: { recordedDemo: boolean; navigate: (view: string) => void }) {
  const [setup, setSetup] = useState<Setup | null>(null);
  const [profile, setProfile] = useState({ company_name: "", industry: "MANUFACTURING", country_code: "" });
  const [entity, setEntity] = useState({ name: "", country_code: "", functional_currency: "" });
  const [busy, setBusy] = useState(false), [message, setMessage] = useState("");
  async function call(action: string, body?: object) {
    const response = await fetch(`/api/company?action=${action}`, { method: body ? "POST" : "GET", headers: body ? { "Content-Type": "application/json" } : undefined, body: body ? JSON.stringify(body) : undefined, cache: "no-store" });
    const value = await response.json();
    if (!response.ok) throw new Error(value.error ?? "Company setup unavailable");
    return value as Setup;
  }
  function apply(value: Setup) {
    setSetup(value);
    if (value.profile) setProfile({ company_name: value.profile.company_name, industry: value.profile.industry, country_code: value.profile.country_code });
  }
  async function load() {
    setBusy(true); setMessage("");
    try { apply(await call("setup")); } catch (error) { setSetup(null); setMessage((error as Error).message); } finally { setBusy(false); }
  }
  useEffect(() => {
    if (recordedDemo) return;
    let cancelled = false;
    call("setup").then(value => { if (!cancelled) apply(value); }).catch(error => { if (!cancelled) setMessage(error.message); });
    return () => { cancelled = true; };
  }, [recordedDemo]);
  const editable = !recordedDemo && Boolean(setup?.can_edit) && !busy;
  return <section className="company-workspace">
    <div className="panel"><p className="eyebrow">A WORKSPACE FOR YOUR BUSINESS</p><h2>Set up your company</h2><p>Use one workspace for your company’s cash, forecasts, funding and risks. Manufacturing, services, retail, energy and other businesses follow the same treasury workflow.</p><p className="muted">Each customer needs a separate deployment, database and company sign-in configuration. This version does not provide shared hosting for multiple companies.</p>
      {recordedDemo ? <div className="demo-notice"><div><strong>Preview of company setup</strong><p>The public site uses fictional data. Saving a company needs a hosted backend and company sign-in. No company has been registered here.</p></div></div> : <><button className="button secondary" onClick={load} disabled={busy}>{busy ? "Loading…" : "Reload company setup"}</button><p className="muted">An active company account can view setup. The Group Treasurer can save changes. Staff roles are assigned through your company’s controlled account provisioning.</p></>}
    </div>
    <div className="company-steps" aria-label="Company onboarding steps">
      <article className="panel"><span className="badge">1 · Company</span><h3>{setup?.profile ? setup.profile.company_name : "Register your business"}</h3><p>{setup?.profile ? "Profile saved. This is setup metadata, not production approval." : "Enter your company name, industry and home country below."}</p></article>
      <article className="panel"><span className="badge">2 · Data</span><h3>Connect banks and ERP</h3><p>Review mappings, reconciliation and source evidence before activation.</p><button className="text-button" onClick={() => navigate("integrations")}>Review data connections →</button></article>
      <article className="panel"><span className="badge">3 · Daily work</span><h3>Plan and monitor cash</h3><p>Check forecasts and risks. Test assumptions in private cash planning.</p><button className="text-button" onClick={() => navigate("planning")}>Open cash planning →</button></article>
      <article className="panel"><span className="badge warning">4 · Approval</span><h3>Verify before real use</h3><p>Independent reviews and named sign-offs remain required.</p><button className="text-button" onClick={() => navigate("governance")}>Review readiness →</button></article>
    </div>
    <p role="status" aria-live="polite">{message}</p>
    <div className="company-columns">
      <article className="panel"><h2>Company profile</h2><p className="muted">Reporting currency: {setup?.reporting_currency ?? "Set by deployment configuration"}. Changing this requires an operator-led engine configuration review.</p>
        <form className="company-form" onSubmit={async e => { e.preventDefault(); setBusy(true); setMessage(""); try { apply(await call("profile", { ...profile, expected_version: setup?.profile?.version ?? 0 })); setMessage("Company profile saved. Production evidence and gates are unchanged."); } catch (error) { setMessage((error as Error).message); } finally { setBusy(false); } }}>
          <fieldset disabled={!editable}><legend>Business details</legend>
            <label>Company name<input required maxLength={160} value={profile.company_name} onChange={e => setProfile({ ...profile, company_name: e.target.value })} /></label>
            <label>Industry<select value={profile.industry} onChange={e => setProfile({ ...profile, industry: e.target.value })}>{industries.map(value => <option key={value} value={value}>{label(value)}</option>)}</select></label>
            <label>Home country code<input required pattern="[A-Z]{2}" maxLength={2} placeholder="IN, GB, US" value={profile.country_code} onChange={e => setProfile({ ...profile, country_code: e.target.value.toUpperCase() })} /><small>Two-letter country code; jurisdiction-specific reviews remain required.</small></label>
            <button className="button secondary">Save company profile</button>
          </fieldset>
        </form>
      </article>
      <article className="panel"><h2>Register a legal entity</h2><p className="muted">Add a subsidiary or operating company for review. Registration does not add it to treasury calculations, set cash buffers, open bank accounts or certify its legal status.</p>
        <form className="company-form" onSubmit={async e => { e.preventDefault(); setBusy(true); setMessage(""); try { apply(await call("entities", entity)); setEntity({ name: "", country_code: "", functional_currency: "" }); setMessage("Entity registered for review. It has not been activated in the treasury engine."); } catch (error) { setMessage((error as Error).message); } finally { setBusy(false); } }}>
          <fieldset disabled={!editable || !setup?.profile}><legend>Pending entity</legend>
            <label>Legal entity name<input required maxLength={160} value={entity.name} onChange={e => setEntity({ ...entity, name: e.target.value })} /></label>
            <label>Country code<input required pattern="[A-Z]{2}" maxLength={2} placeholder="IN, GB, US" value={entity.country_code} onChange={e => setEntity({ ...entity, country_code: e.target.value.toUpperCase() })} /></label>
            <label>Functional currency code<input required pattern="[A-Z]{3}" maxLength={3} placeholder="INR, GBP, USD" value={entity.functional_currency} onChange={e => setEntity({ ...entity, functional_currency: e.target.value.toUpperCase() })} /><small>Code recorded for review; currency and FX support must be verified.</small></label>
            <button className="button secondary">Register for review</button>
          </fieldset>
        </form>
      </article>
    </div>
    <article className="panel"><h2>Entities and people</h2><h3>Pending entity registrations</h3>{setup?.registrations.length ? <ul className="bullet-list">{setup.registrations.map(e => <li key={e.id}>{e.name} · {e.country_code} · {e.functional_currency} · Pending review</li>)}</ul> : <p className="muted">No pending registrations loaded.</p>}
      <h3>Entities configured in the treasury engine</h3>{setup?.entities.length ? <ul className="bullet-list">{setup.entities.map(e => <li key={e.id}>{e.name} · {e.functional_currency} · {e.active ? "Configured active" : "Inactive"}</li>)}</ul> : <p className="muted">No engine entities loaded. Pending registrations need a separate reviewed configuration process.</p>}
      <h3>Company staff roles</h3>{setup?.users.length ? <ul className="bullet-list">{setup.users.map((u, i) => <li key={i}>{u.display_name} · {label(u.role)}</li>)}</ul> : <p className="muted">No staff directory loaded. Your operator must provision verified accounts and roles; this screen cannot grant access.</p>}
    </article>
  </section>;
}
