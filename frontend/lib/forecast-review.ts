export type ForecastPoint = { week: number; date: string; closing: string };
export type ForecastPair = ForecastPoint & { actual: string | null; difference: string | null };

const limit = 100000000000000n;
function cents(value: string): bigint {
  if (!/^-?\d{1,13}(?:\.\d{1,2})?$/.test(value)) throw new Error("Enter a USD amount with up to two decimal places.");
  const negative = value.startsWith("-"), [whole, fraction = ""] = value.replace(/^-/, "").split(".");
  const amount = BigInt(whole) * 100n + BigInt(fraction.padEnd(2, "0"));
  if (amount > limit) throw new Error("Amounts must be no larger than 1 trillion USD.");
  return negative ? -amount : amount;
}
const absolute = (value: bigint) => value < 0n ? -value : value;
function roundedDivide(value: bigint, denominator: bigint) {
  const result = (absolute(value) + denominator / 2n) / denominator;
  return value < 0n ? -result : result;
}
function decimal(value: bigint) {
  const amount = absolute(value);
  return `${value < 0n ? "-" : ""}${amount / 100n}.${String(amount % 100n).padStart(2, "0")}`;
}
function validDate(value: string) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const date = new Date(`${value}T00:00:00Z`);
  return Number.isFinite(date.getTime()) && date.toISOString().slice(0, 10) === value;
}

/** Compare weekly closing balances for the exact dates supplied by the plan. */
export function reviewForecast(points: ForecastPoint[], actuals: Record<string, string>) {
  if (points.length > 52) throw new Error("Review up to 52 weeks at a time.");
  const dates = new Set<string>(), weeks = new Set<number>();
  for (const point of points) {
    if (!Number.isInteger(point.week) || point.week < 1 || point.week > 52 || !validDate(point.date) || dates.has(point.date) || weeks.has(point.week)) throw new Error("Each plan week needs a unique valid date and week number.");
    cents(point.closing); dates.add(point.date); weeks.add(point.week);
  }
  const errors: Record<string, string> = {};
  let count = 0, absoluteError = 0n, signedError = 0n, absoluteActual = 0n;
  for (const key of Object.keys(actuals)) if (!dates.has(key) && actuals[key].trim()) errors[key] = "This date is outside the selected plan.";
  const pairs: ForecastPair[] = points.map(point => {
    const input = (actuals[point.date] ?? "").trim();
    if (!input) return { ...point, actual: null, difference: null };
    try {
      const actual = cents(input), difference = actual - cents(point.closing);
      count++; absoluteError += absolute(difference); signedError += difference; absoluteActual += absolute(actual);
      return { ...point, actual: decimal(actual), difference: decimal(difference) };
    } catch (error) {
      errors[point.date] = (error as Error).message;
      return { ...point, actual: null, difference: null };
    }
  });
  return {
    pairs, errors, count, missing: points.length - count,
    meanAbsoluteError: count ? decimal(roundedDivide(absoluteError, BigInt(count))) : null,
    bias: count ? decimal(roundedDivide(signedError, BigInt(count))) : null,
    wapePercent: count && absoluteActual ? decimal(roundedDivide(absoluteError * 10000n, absoluteActual)) : null,
  };
}
