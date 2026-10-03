from sqlalchemy.orm import Session
from app.agents.base import TreasuryAgent
from app.schemas.treasury import AgentFinding
from app.services.mvp14_forecast_working_capital import calculate_receivables_aging


class ReceivablesCollectionRiskAgent(TreasuryAgent):
    name = "Receivables Collection Risk Agent"

    def run(self, db: Session) -> list[AgentFinding]:
        x = calculate_receivables_aging(db)
        share = float(x.overdue_share)
        has_90_plus = any(b.bucket == "90+" and b.invoice_count > 0 for b in x.buckets)
        has_61_90 = any(b.bucket == "61-90" and b.invoice_count > 0 for b in x.buckets)
        sev = "HIGH" if share >= 0.30 or has_90_plus else "MEDIUM" if share >= 0.15 or has_61_90 else "INFO"
        return [AgentFinding(
            agent=self.name,
            severity=sev,
            title="Receivables aging and collection dependency",
            message=f"Open AR={x.total_open_receivables}; overdue={x.total_overdue_receivables} ({share:.1%}); probability-weighted AR={x.probability_weighted_open_receivables}.",
            metric=str(x.overdue_share),
        )]
