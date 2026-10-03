type Props = { label: string; value: string; sub?: string };

export function MetricCard({ label, value, sub }: Props) {
  return (
    <article className="card">
      <p className="eyebrow">{label}</p>
      <strong className="metric">{value}</strong>
      {sub ? <p className="muted">{sub}</p> : null}
    </article>
  );
}
