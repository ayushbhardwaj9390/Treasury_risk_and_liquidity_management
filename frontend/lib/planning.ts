// Private planning only. Fixed-point arithmetic is checked against the Python forecast engine.
export const categories = ["CRUDE_PURCHASE", "PRODUCT_SALE", "FREIGHT", "OPERATING", "OTHER"];
export const currencies = ["USD", "GBP", "SGD", "EUR", "INR", "JPY", "CHF", "CAD", "AUD", "CNY", "AED", "HKD"];
export type Flow = { id: string; entity: string; date: string; direction: "INFLOW" | "OUTFLOW"; currency: string; amount: string; category: string; probability: string };
export type Mapping = Record<"id" | "entity" | "date" | "direction" | "currency" | "amount" | "category" | "probability", string>;
export type Assumptions = { start: string; weeks: number; opening: string; buffer: string; rates: Record<string, string>; delay: number; receipts: number; costs: number; oil: number; fx: number };
const scale = 10n ** 32n;
const dayMillis = 86400000;
export function decimal(value: string, places = 6): bigint {
  if (!new RegExp(`^\\d{1,13}(?:\\.\\d{1,${places}})?$`).test(value)) throw Error("Use a positive plain number, without commas or currency symbols.");
  const [whole, fraction = ""] = value.split(".");
  return BigInt(whole) * scale + BigInt((fraction + "0".repeat(32)).slice(0, 32));
}
function multiply(a: bigint, b: bigint) { return a * b / scale; }
export function dollars(value: bigint) {
  const sign = value < 0n ? "-" : "", abs = value < 0n ? -value : value;
  const cents = (abs + scale / 200n) / (scale / 100n);
  return `${sign}${cents / 100n}.${String(cents % 100n).padStart(2, "0")}`;
}
export function validDate(value: string) {
  return /^\d{4}-\d{2}-\d{2}$/.test(value) && Number(value.slice(0, 4)) >= 1 && Number.isFinite(Date.parse(`${value}T00:00:00Z`)) && new Date(`${value}T00:00:00Z`).toISOString().slice(0, 10) === value;
}
function dateDays(value: string) { return Date.parse(`${value}T00:00:00Z`) / dayMillis; }
function dateString(value: number) { return new Date(value * dayMillis).toISOString().slice(0, 10); }

export function parseCsv(text: string, delimiter = ",") {
  if (new TextEncoder().encode(text).length > 524288) throw Error("Use a file under 512 KB.");
  if (![",", ";", "\t"].includes(delimiter)) throw Error("Unsupported separator.");
  const records: string[][] = [], row: string[] = [];
  let value = "", quoted = false, closed = false;
  text = text.replace(/^\uFEFF/, "");
  const field = () => { row.push(value.trim()); value = ""; closed = false; };
  const record = () => { field(); if (row.some(Boolean)) records.push([...row]); row.length = 0; };
  for (let i = 0; i < text.length; i++) {
    const char = text[i];
    if (quoted) { if (char === '"') { if (text[i + 1] === '"') { value += '"'; i++; } else { quoted = false; closed = true; } } else value += char; }
    else if (char === delimiter) field();
    else if (char === "\n" || char === "\r") { if (char === "\r" && text[i + 1] === "\n") i++; record(); }
    else if (char === '"' && !value && !closed) quoted = true;
    else { if (closed || char === '"') throw Error("Malformed CSV quotation. Export a fresh CSV file."); value += char; }
    if (records.length > 501) throw Error("Use at most 500 cash-flow records.");
  }
  if (quoted) throw Error("The file has an unfinished quoted field.");
  if (value || row.length || closed) record();
  const headers = records.shift() ?? [];
  if (!headers.length || headers.some(h => !h) || new Set(headers).size !== headers.length) throw Error("The header row must have unique, non-empty column names.");
  if (records.length > 500 || headers.length > 30) throw Error("Use at most 500 records and 30 columns.");
  if (records.some(r => r.length !== headers.length)) throw Error("Some records have more or fewer columns than the header.");
  if (!records.length) throw Error("The file contains no cash flows.");
  return { headers, rows: records.map(r => Object.fromEntries(headers.map((h, i) => [h, r[i]]))) };
}
export function validateRows(rows: Record<string, string>[], mapping: Mapping) {
  const flows: Flow[] = [], errors: string[] = [], ids = new Set<string>();
  if (!["id", "date", "amount"].every(k => mapping[k as keyof Mapping])) return { flows, errors: ["Map reference, date and amount before checking the file."] };
  rows.forEach((row, index) => {
    const get = (key: keyof Mapping) => row[mapping[key]] ?? "";
    try {
      const id = get("id"), date = get("date"), raw = get("amount");
      if (!/^[A-Za-z0-9][A-Za-z0-9_.\-]{0,79}$/.test(id)) throw Error("Reference must use letters, numbers, dot, underscore or dash, and start with a letter or number.");
      if (ids.has(id)) throw Error(`Duplicate reference: ${id}.`);
      if (!validDate(date)) throw Error("Date must be a valid YYYY-MM-DD date.");
      const currency = get("currency").toUpperCase() || "USD";
      if (!currencies.includes(currency)) throw Error(`Unsupported currency ${currency}.`);
      let direction = get("direction").toUpperCase();
      direction = ({ CREDIT: "INFLOW", RECEIVABLE: "INFLOW", DEBIT: "OUTFLOW", PAYABLE: "OUTFLOW" } as Record<string, string>)[direction] ?? direction;
      if (!direction) direction = raw.startsWith("-") ? "OUTFLOW" : "INFLOW";
      if (!["INFLOW", "OUTFLOW"].includes(direction)) throw Error("Direction must be INFLOW / OUTFLOW or CREDIT / DEBIT.");
      if (raw.startsWith("-") && direction !== "OUTFLOW") throw Error("A negative amount conflicts with an inflow direction.");
      const amount = raw.replace(/^-/, "");
      if (decimal(amount, 2) <= 0n || decimal(amount, 2) > decimal("1000000000000")) throw Error("Amount must be greater than zero and no more than one trillion, with at most two decimals.");
      const category = get("category").toUpperCase() || "OTHER";
      if (!categories.includes(category)) throw Error(`Category must be ${categories.join(", ")}.`);
      if (category === "CRUDE_PURCHASE" && direction !== "OUTFLOW" || category === "PRODUCT_SALE" && direction !== "INFLOW") throw Error("Crude purchases must be outflows and product sales must be inflows.");
      const probability = get("probability") || "1";
      if (decimal(probability, 4) > scale || direction === "OUTFLOW" && decimal(probability, 4) !== scale) throw Error("Receipt probability must be from 0 to 1; payments must stay at 1.");
      const entity = get("entity") || "GROUP";
      if (entity.length > 120) throw Error("Entity name must be under 120 characters.");
      ids.add(id); flows.push({ id, entity, date, direction: direction as Flow["direction"], currency, amount, category, probability });
    } catch (error) { errors.push(`Record ${index + 1}: ${(error as Error).message}`); }
  });
  return { flows, errors };
}
export function simulate(flows: Flow[], assumptions: Assumptions) {
  if (!validDate(assumptions.start) || !Number.isInteger(assumptions.weeks) || assumptions.weeks < 1 || assumptions.weeks > 52) throw Error("Choose a valid start date and a horizon from 1 to 52 weeks.");
  if (!Number.isInteger(assumptions.delay) || assumptions.delay < 0 || assumptions.delay > 90) throw Error("Receipt delay must be from 0 to 90 days.");
  for (const k of ["receipts", "costs", "oil", "fx"] as const) if (!Number.isFinite(assumptions[k]) || assumptions[k] < -100 || assumptions[k] > 200 || Math.abs(Math.round(assumptions[k] * 10) - assumptions[k] * 10) > 1e-9) throw Error("Cash changes must be from -100% to +200% in 0.1% steps.");
  const factor = (value: number) => scale + BigInt(Math.round(value * 10)) * (scale / 1000n);
  let cash = decimal(assumptions.opening, 2), maximum = 0n, breach: number | null = null;
  const buffer = decimal(assumptions.buffer, 2), start = dateDays(assumptions.start), end = start + assumptions.weeks * 7;
  const buckets = Array.from({ length: assumptions.weeks }, () => ({ inflows: 0n, outflows: 0n }));
  let overdue = 0, beyond = 0, excludedAmount = 0n;
  for (const flow of flows) {
    const rate = flow.currency === "USD" ? "1" : assumptions.rates[flow.currency];
    if (!rate || decimal(rate) <= 0n || decimal(rate) > decimal("1000000")) throw Error(`Provide a positive assumed USD exchange rate for ${flow.currency}.`);
    let amount = multiply(decimal(flow.amount, 2), decimal(rate));
    if (flow.currency !== "USD") amount = multiply(amount, factor(assumptions.fx));
    if (["CRUDE_PURCHASE", "PRODUCT_SALE"].includes(flow.category)) amount = multiply(amount, factor(assumptions.oil));
    if (flow.direction === "INFLOW") amount = multiply(multiply(amount, decimal(flow.probability, 4)), factor(assumptions.receipts));
    else amount = multiply(amount, factor(assumptions.costs));
    const originalDay = dateDays(flow.date), day = originalDay + (flow.direction === "INFLOW" ? assumptions.delay : 0);
    if (originalDay < start) { overdue++; excludedAmount += amount; continue; }
    if (day >= end) { beyond++; excludedAmount += amount; continue; }
    const bucket = buckets[Math.floor((day - start) / 7)];
    if (flow.direction === "INFLOW") bucket.inflows += amount; else bucket.outflows += amount;
  }
  const points = buckets.map((bucket, index) => {
    const opening = cash;
    cash += bucket.inflows - bucket.outflows;
    const headroom = cash - buffer, shortfall = headroom < 0n ? -headroom : 0n;
    if (shortfall > maximum) maximum = shortfall;
    if (shortfall > 0n && breach === null) breach = index + 1;
    return { week: index + 1, date: dateString(start + index * 7), opening: dollars(opening), inflows: dollars(bucket.inflows), outflows: dollars(bucket.outflows), closing: dollars(cash), buffer: dollars(buffer), headroom: dollars(headroom), shortfall: dollars(shortfall) };
  });
  return { ending: dollars(cash), headroom: dollars(cash - buffer), maximumShortfall: dollars(maximum), firstBreach: breach, overdue, beyond, excludedAmount: dollars(excludedAmount), points };
}
