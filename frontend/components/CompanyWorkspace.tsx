"use client";
import { useEffect, useState } from "react";

import { emptyDemoSetup, saveDemoProfile, registerDemoEntity, exampleDemoSetup, industries, type Setup } from "../lib/company-demo";
const label = (value: string) => value.replaceAll("_", " ").toLowerCase();

export default function CompanyWorkspace({ recordedDemo, navigate }: { recordedDemo: boolean; navigate: (view: string) => void }) {
  const [setup, setSetup] = useState<Setup | null>(recordedDemo ? emptyDemoSetup() : null);
  const [profile, setProfile] = useState({ company_name: "", industry: "MANUFACTURING", country_code: "" });
  const [entity, setEntity] = useState({ name: "", country_code: "", functional_currency: "" });
  const [busy, setBusy] = useState(!recordedDemo), [message, setMessage] = useState("");
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
    setBusy(true);
    call("setup").then(value => { if (!cancelled) apply(value); }).catch(error => { if (!cancelled) setMessage(error.message); }).finally(() => { if (!cancelled) setBusy(false); });
    return () => { cancelled = true; };
  }, [recordedDemo]);
  const editable = (recordedDemo || Boolean(setup?.can_edit)) && !busy;
  const hasDraft = Boolean(setup?.profile || setup?.registrations.length || profile.company_name || profile.country_code || entity.name || entity.country_code || entity.functional_currency);
  function startExample(structure: "single" | "multinational") {
    if (!recordedDemo || hasDraft || busy) return;
    apply(exampleDemoSetup(structure));
    setMessage("Fictional example loaded. Edit the profile or add entities below. No engine or server records were created.");
  }
  function downloadDraft() {
    if (!recordedDemo || !setup?.profile) return;
    const content = { format: "treasury-demo-onboarding-v1", fictional: true, production_approved: false, profile: setup.profile, pending_entities: setup.registrations };
    const url = URL.createObjectURL(new Blob([JSON.stringify(content, null, 2)], { type: "application/json" }));
    const anchor = document.createElement("a"); anchor.href = url; anchor.download = "treasury-demo-company-draft.json"; anchor.click(); URL.revokeObjectURL(url);
    setMessage("Saved a copy of the demo draft to your device. This is not a cash-flow CSV or production registration; importing it is not supported.");
  }
  return <section className="company-workspace">
    <article className="panel next-step"><p className="eyebrow">YOUR NEXT STEP</p><h2>{!setup?.profile ? "Tell us about your business" : !setup.registrations.length ? "Add your first operating company" : "Try your first cash-flow plan"}</h2><p>{!setup?.profile ? "Save a name, industry and home country. You can also choose a fictional example below." : !setup.registrations.length ? "A legal entity is a separately registered business, such as your main company or a subsidiary." : "Your setup details are saved. Test a sample, paste an Excel table or upload a CSV; this does not activate real accounts."}</p>{!setup?.profile ? <a className="button secondary" href="#company-profile">Enter business details ↓</a> : !setup.registrations.length ? <a className="button secondary" href="#company-entity">Add operating company ↓</a> : <button className="button secondary" onClick={() => navigate("planning")}>Continue to cash planning →</button>}</article>
    <div className="panel"><p className="eyebrow">A WORKSPACE FOR YOUR BUSINESS</p><h2>Set up your company</h2><p>Enter your business details, add the companies you operate, then test a cash-flow plan.</p><details><summary>Requirements for real company use</summary><p>Each customer needs a separate deployment, database and company sign-in. Verified connections, staff roles and production approvals are required. Shared hosting for unrelated companies is not supported.</p></details>
      {recordedDemo ? <div className="demo-notice"><div><strong>Editable dummy company setup · this session only</strong><p>Enter fictional details and save a demo profile, then add domestic or overseas entities. Nothing is sent to a server or added to treasury calculations. Switching screens keeps your draft; reloading clears it. Real company registration still needs the hosted backend and company sign-in.</p><button type="button" className="button secondary" onClick={() => { setSetup(emptyDemoSetup()); setProfile({ company_name: "", industry: "MANUFACTURING", country_code: "" }); setEntity({ name: "", country_code: "", functional_currency: "" }); setMessage("Dummy setup cleared from this session."); }}>Clear demo setup</button></div></div> : <><button className="button secondary" onClick={load} disabled={busy}>{busy ? "Loading…" : "Reload company setup"}</button><p className="muted">An active company account can view setup. The Group Treasurer can save changes. Staff roles are assigned through your company’s controlled account provisioning.</p></>}
    </div>
    {recordedDemo && <article className="panel"><h2>Choose how to start</h2><p>Enter a blank company below, or try a fictional example with entities already drafted. Both examples use an oil-products business; you can change the industry and names.</p><div className="company-columns"><div><h3>Single-country company</h3><p>One US entity with USD as its functional currency.</p><button className="button secondary" disabled={hasDraft || busy} onClick={() => startExample("single")}>Try single-country example</button></div><div><h3>Multinational group</h3><p>Three entities in the US, Germany and UK, using USD, EUR and GBP.</p><button className="button secondary" disabled={hasDraft || busy} onClick={() => startExample("multinational")}>Try multinational example</button></div></div>{hasDraft && <p className="muted">Your current draft is kept. Use Clear demo setup above if you want to start a different example.</p>}</article>}
    <datalist id="company-country-options">{[["US","United States"],["IN","India"],["GB","United Kingdom"],["DE","Germany"],["SG","Singapore"],["AE","United Arab Emirates"],["CA","Canada"],["AU","Australia"]].map(([code,name]) => <option key={code} value={code}>{name}</option>)}</datalist>
    <datalist id="company-currency-options">{[["USD","US dollar"],["INR","Indian rupee"],["GBP","Pound sterling"],["EUR","Euro"],["SGD","Singapore dollar"],["AED","UAE dirham"],["CAD","Canadian dollar"],["AUD","Australian dollar"],["JPY","Japanese yen"]].map(([code,name]) => <option key={code} value={code}>{name}</option>)}</datalist>
    <p role="status" aria-live="polite">{message}</p>
    <div className="company-columns">
      <article className="panel" id="company-profile"><h2>1. Company profile</h2><p className="muted">Reporting currency: {setup?.reporting_currency ?? "Set by deployment configuration"}. {recordedDemo ? "USD is assumed for this dummy setup; it does not configure the treasury engine." : "Changing this requires an operator-led engine configuration review."}</p>
        <form className="company-form" onSubmit={async e => { e.preventDefault(); setBusy(true); setMessage(""); try { if (recordedDemo) { apply(saveDemoProfile(setup ?? emptyDemoSetup(), profile)); setMessage("Demo profile saved only in this session. You can now add demo entities."); } else { apply(await call("profile", { ...profile, expected_version: setup?.profile?.version ?? 0 })); setMessage("Company profile saved. Production evidence and gates are unchanged."); } } catch (error) { setMessage((error as Error).message); } finally { setBusy(false); } }}>
          <fieldset disabled={!editable}><legend>Business details</legend>
            <label>Company name<input required maxLength={160} value={profile.company_name} onChange={e => setProfile({ ...profile, company_name: e.target.value })} /></label>
            <label>Industry<select value={profile.industry} onChange={e => setProfile({ ...profile, industry: e.target.value })}>{industries.map(value => <option key={value} value={value}>{label(value)}</option>)}</select></label>
            <label>Home country code<input list="company-country-options" required pattern="[A-Z]{2}" maxLength={2} placeholder="IN, GB, US" value={profile.country_code} onChange={e => setProfile({ ...profile, country_code: e.target.value.toUpperCase() })} /><small>Choose a suggestion or enter a two-letter code. Jurisdiction-specific reviews remain required.</small></label>
            <button className="button secondary">{recordedDemo ? "Save demo profile" : "Save company profile"}</button>
          </fieldset>
        </form>
      </article>
      <article className="panel" id="company-entity"><h2>2. Add an operating company</h2><p className="muted">Add a subsidiary or operating company for review. Registration does not add it to treasury calculations, set cash buffers, open bank accounts or certify its legal status.</p>
        {!setup?.profile && <p className="muted">Save {recordedDemo ? "the demo" : "your"} company profile first to unlock these fields.</p>}<form className="company-form" onSubmit={async e => { e.preventDefault(); setBusy(true); setMessage(""); try { if (recordedDemo) { apply(registerDemoEntity(setup ?? emptyDemoSetup(), entity)); setMessage("Demo entity added only in this session. Treasury engine entities are unchanged."); } else { apply(await call("entities", entity)); setMessage("Entity registered for review. It has not been activated in the treasury engine."); } setEntity({ name: "", country_code: "", functional_currency: "" }); } catch (error) { setMessage((error as Error).message); } finally { setBusy(false); } }}>
          <fieldset disabled={!editable || !setup?.profile}><legend>Pending entity</legend>
            <label>Legal entity name<input required maxLength={160} value={entity.name} onChange={e => setEntity({ ...entity, name: e.target.value })} /></label>
            <label>Country code<input list="company-country-options" required pattern="[A-Z]{2}" maxLength={2} placeholder="IN, GB, US" value={entity.country_code} onChange={e => setEntity({ ...entity, country_code: e.target.value.toUpperCase() })} /></label>
            <label>Functional currency code<input list="company-currency-options" required pattern="[A-Z]{3}" maxLength={3} placeholder="INR, GBP, USD" value={entity.functional_currency} onChange={e => setEntity({ ...entity, functional_currency: e.target.value.toUpperCase() })} /><small>Choose a suggestion or enter a code. Currency and FX support must be verified.</small></label>
            <button className="button secondary">{recordedDemo ? "Add demo entity" : "Register for review"}</button>
          </fieldset>
        </form>
      </article>
    </div>
    <article className="panel"><h2>Your onboarding checklist</h2><p>{Number(Boolean(setup?.profile)) + Number(Boolean(setup?.registrations.length))} of 2 setup metadata steps complete. Data connections and production approval require separate evidence.</p><ol className="bullet-list"><li><strong>Company profile:</strong> {setup?.profile ? recordedDemo ? "Demo saved" : "Saved" : "Enter and save business details"}.</li><li><strong>Legal entities:</strong> {setup?.registrations.length ? `${setup.registrations.length} pending ${recordedDemo ? "demo drafts" : "registrations"}` : "Add at least one operating company"}. Pending entries are not active engine entities.</li><li><strong>Cash-flow test:</strong> Upload a CSV in Cash planning and check your results. <button className="text-button" onClick={() => navigate("planning")}>Start cash-flow test →</button></li><li><strong>Bank and ERP connections:</strong> {recordedDemo ? "Not connected in this demo" : "Verify mappings and source evidence in Data connections"}. <button className="text-button" onClick={() => navigate("integrations")}>Review connections →</button></li><li><strong>Staff access and real use:</strong> Verified accounts, reviewed roles and readiness sign-offs are required. <button className="text-button" onClick={() => navigate("governance")}>Review remaining gates →</button></li></ol>{recordedDemo && <><button className="button secondary" disabled={!setup?.profile} onClick={downloadDraft}>Download demo setup draft</button><p className="muted">Save a JSON copy before reloading. This download is for reference; it cannot be uploaded into the cash planner or restored automatically.</p></>}</article>
    <article className="panel"><h2>Entities and people</h2><h3>Pending entity registrations</h3>{setup?.registrations.length ? <ul className="bullet-list">{setup.registrations.map(e => <li key={e.id}>{e.name} · {e.country_code} · {e.functional_currency} · {recordedDemo ? "Demo draft · not registered with a server" : "Pending review"}</li>)}</ul> : <p className="muted">No pending registrations loaded.</p>}
      <details><summary>Advanced: configured entities and staff roles</summary><h3>Entities configured in the treasury engine</h3>{setup?.entities.length ? <ul className="bullet-list">{setup.entities.map(e => <li key={e.id}>{e.name} · {e.functional_currency} · {e.active ? "Configured active" : "Inactive"}</li>)}</ul> : <p className="muted">No engine entities loaded. Pending registrations need a separate reviewed configuration process.</p>}
      <h3>Company staff roles</h3>{setup?.users.length ? <ul className="bullet-list">{setup.users.map((u, i) => <li key={i}>{u.display_name} · {label(u.role)}</li>)}</ul> : <p className="muted">No staff directory loaded. Your operator must provision verified accounts and roles; this screen cannot grant access.</p>}</details>
    </article>
  </section>;
}
