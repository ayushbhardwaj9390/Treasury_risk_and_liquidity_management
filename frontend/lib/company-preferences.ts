export const countries = ["US", "GB", "IN", "DE", "FR", "SG", "AE", "HK", "CN", "JP", "CH", "CA", "AU", "NL", "SA", "BR", "ZA"];
export const currencies = ["USD", "GBP", "INR", "EUR", "SGD", "AED", "HKD", "CNY", "JPY", "CHF", "CAD", "AUD"];
export const reviewerRoles = ["TREASURY_MANAGER", "GROUP_TREASURER", "RISK_MANAGER", "AUDITOR"];
export type Preferences = { countries: string[]; currencies: string[]; minimum_cash_usd: string; reviewer_roles: string[] };
export type PreferenceState = { can_edit: boolean; status: "DRAFT_NOT_ACTIVATED"; draft: (Preferences & { version: number; updated_by?: string; updated_at?: string }) | null };
export function examplePreferences(): Preferences { return { countries: ["US"], currencies: ["USD"], minimum_cash_usd: "1000", reviewer_roles: ["GROUP_TREASURER", "RISK_MANAGER"] }; }
export function validatePreferences(value: Preferences): Preferences {
  for (const [values, allowed] of [[value.countries, countries], [value.currencies, currencies], [value.reviewer_roles, reviewerRoles]]) {
    if (!Array.isArray(values) || !values.length || values.length > allowed.length || new Set(values).size !== values.length || values.some(v => !allowed.includes(v))) throw new Error("Choose at least one unique supported value in each list.");
  }
  if (typeof value.minimum_cash_usd !== "string" || !/^(0|[1-9][0-9]{0,11})(\.[0-9]{1,2})?$/.test(value.minimum_cash_usd)) throw new Error("Enter a non-negative USD target with up to two decimal places, below one trillion.");
  return { countries: [...value.countries], currencies: [...value.currencies], minimum_cash_usd: value.minimum_cash_usd, reviewer_roles: [...value.reviewer_roles] };
}
