// Session-only dummy metadata. No network, storage, roles or treasury engine writes.
export const industries = ["MANUFACTURING", "ENERGY", "SERVICES", "RETAIL", "FINANCIAL_SERVICES", "OTHER"];
export type Profile = { company_name: string; industry: string; country_code: string; version: number };
export type Entity = { id: number; name: string; country_code: string; functional_currency: string; status?: string; active?: boolean };
export type Setup = { profile: Profile | null; reporting_currency: string; can_edit: boolean; registrations: Entity[]; entities: Entity[]; users: { display_name: string; role: string }[] };
export function emptyDemoSetup(): Setup { return { profile: null, reporting_currency: "USD", can_edit: true, registrations: [], entities: [], users: [] }; }
function name(value: string) { const result = value.trim(); if (!result || result.length > 160) throw Error("Enter a name with 1–160 characters."); return result; }
function code(value: string, length: number) { const result = value.trim().toUpperCase(); if (!(length === 2 ? /^[A-Z]{2}$/ : /^[A-Z]{3}$/).test(result)) throw Error(`Enter a ${length}-letter country or currency code.`); return result; }
export function saveDemoProfile(setup: Setup, profile: Omit<Profile, "version">): Setup {
  if (!industries.includes(profile.industry)) throw Error("Choose a supported industry.");
  return { ...setup, profile: { company_name: name(profile.company_name), industry: profile.industry, country_code: code(profile.country_code, 2), version: (setup.profile?.version ?? 0) + 1 } };
}
export function registerDemoEntity(setup: Setup, entity: Pick<Entity, "name" | "country_code" | "functional_currency">): Setup {
  if (!setup.profile) throw Error("Save the demo company profile first.");
  const entityName = name(entity.name);
  if (setup.registrations.some(row => row.name.toLowerCase() === entityName.toLowerCase())) throw Error("This demo entity name is already registered.");
  return { ...setup, registrations: [...setup.registrations, { id: setup.registrations.length + 1, name: entityName, country_code: code(entity.country_code, 2), functional_currency: code(entity.functional_currency, 3), status: "DEMO_DRAFT" }] };
}
