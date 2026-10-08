import type { DemoSnapshot } from "../lib/automatic-demo";
import { explainWarnings } from "../lib/warning-explanations";

export default function WarningReview({ snapshot }: { snapshot: DemoSnapshot | null }) {
  const warnings = explainWarnings(snapshot);
  return <article className="panel"><p className="eyebrow">UNDERSTAND THE WARNINGS · FICTIONAL DATA</p><h2>Why does this need attention?</h2><p>Open a warning to see the numbers behind it and what a person should review. These checks use only this example’s snapshot, not your uploaded company records.</p>
    {warnings === null ? <p role="status">Load a dummy snapshot to see explanations. No warning assessment is available yet.</p> : warnings.length === 0 ? <p>No configured dummy check currently needs attention. This is not a production-readiness approval.</p> : warnings.map(warning => <details key={warning.id}><summary>{warning.title}</summary><p>{warning.cause}</p><strong>Supporting records</strong>{warning.evidence.length ? <div className="table-scroll"><table><thead><tr><th>Reference</th><th>Date</th><th>What this shows</th></tr></thead><tbody>{warning.evidence.map((row, index) => <tr key={`${row.reference}-${index}`}><td>{row.reference}</td><td>{row.date ?? "Not supplied"}</td><td>{row.summary}</td></tr>)}</tbody></table></div> : <p>No supporting event reference was supplied in this snapshot.</p>}<p><strong>What to review next: </strong>{warning.nextStep}</p></details>)}
  </article>;
}
