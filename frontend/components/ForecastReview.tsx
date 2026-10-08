"use client";
import { useState } from "react";
import { reviewForecast, type ForecastPoint } from "../lib/forecast-review";

export default function ForecastReview({ points, source }: { points: ForecastPoint[]; source: string }) {
  // A new plan clears manually entered observations before its first render.
  return <ReviewForm key={JSON.stringify([source, points])} points={points} source={source} />;
}
function ReviewForm({ points, source }: { points: ForecastPoint[]; source: string }) {
  const [actuals, setActuals] = useState<Record<string, string>>({});
  let review: ReturnType<typeof reviewForecast>;
  try { review = reviewForecast(points, actuals); }
  catch (error) { return <section className="panel"><h2>Did the money plan match what happened?</h2><p role="alert">{(error as Error).message}</p></section>; }
  return <section className="panel">
    <h2>Did the money plan match what happened?</h2>
    <p>Plan: {source}. Enter the money actually left at the end of each listed seven-day week, in USD. The date below is the first day of the week. Leave a week empty if you do not know yet. Use fictional amounts when testing this demonstration.</p>
    <p className="muted">These are manual, unverified observations for this session. They do not train an AI, change the plan or update company records.</p>
    <div className="table-scroll"><table><thead><tr><th>Week starting</th><th>Planned closing money (USD)</th><th>Actual closing money (USD)</th><th>Actual minus plan (USD)</th></tr></thead>
      <tbody>{review.pairs.map(point => <tr key={point.date}>
        <td>Week {point.week} · {point.date}</td><td>{point.closing}</td>
        <td><input aria-label={`Actual closing money for ${point.date} in USD`} aria-invalid={!!review.errors[point.date]} aria-describedby={review.errors[point.date] ? `actual-error-${point.date}` : undefined} inputMode="decimal" maxLength={18} placeholder="Not known yet" value={actuals[point.date] ?? ""} onChange={event => setActuals(current => ({ ...current, [point.date]: event.target.value }))} />
          {review.errors[point.date] && <p role="alert" id={`actual-error-${point.date}`}>{review.errors[point.date]}</p>}</td>
        <td>{point.difference ?? "Not compared yet"}</td>
      </tr>)}</tbody></table></div>
    <p>{review.count} of {points.length} weeks compared. {review.missing} weeks still need a valid actual amount.</p>
    <p><strong>Average difference in either direction: </strong>{review.meanAbsoluteError === null ? "Unavailable" : `${review.meanAbsoluteError} USD`}. A smaller number means the plan was closer for these weeks.</p>
    <p><strong>Average actual minus plan: </strong>{review.bias === null ? "Unavailable" : `${review.bias} USD`}. Positive means more money was left than planned; negative means less.</p>
    <details><summary>How is the percentage difference calculated?</summary>
      <p>Total absolute differences divided by total absolute actual closing balances: {review.wapePercent === null ? "unavailable until actual balances have a nonzero total" : `${review.wapePercent}%`}. It can exceed 100%. It measures these closing balances, not overall forecasting accuracy or individual receipts and payments.</p>
    </details>
    <button type="button" className="button secondary" onClick={() => setActuals({})}>Clear actual amounts</button>
  </section>;
}
