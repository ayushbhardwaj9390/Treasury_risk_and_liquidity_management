from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.base import TreasuryAgent
from app.models import CounterpartyLimit, DerivativePosition, FXRate
from app.schemas.treasury import AgentFinding
from app.services.derivative_risk import calculate_counterparty_exposure, derivative_risk_summary


class ModelRiskAgent(TreasuryAgent):
    """Independent challenger for data/model conditions that can invalidate conclusions."""

    name = "Model Risk Challenger"

    def run(self, db: Session) -> list[AgentFinding]:
        findings: list[AgentFinding] = []
        cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=24)
        stale_rates = db.scalars(select(FXRate).where(FXRate.as_of < cutoff)).all()
        if stale_rates:
            findings.append(AgentFinding(
                agent=self.name,
                severity="HIGH",
                title="Market-data freshness challenge",
                message=f"{len(stale_rates)} FX rate record(s) are older than 24 hours; FX and consolidated outputs require review.",
            ))

        derivative_summary = derivative_risk_summary(db)
        if derivative_summary.unmapped_trade_count:
            findings.append(AgentFinding(
                agent=self.name,
                severity="HIGH",
                title="Hedge attribution challenge",
                message="At least one derivative lacks an approved underlying reference; hedge effectiveness and residual exposure conclusions are not fully reliable until mapped.",
            ))

        no_limit = [x.counterparty for x in calculate_counterparty_exposure(db) if x.status == "NO-LIMIT"]
        if no_limit:
            findings.append(AgentFinding(
                agent=self.name,
                severity="HIGH",
                title="Counterparty model-control gap",
                message="Counterparty exposure cannot be assessed against approved risk appetite for: " + ", ".join(no_limit),
            ))

        trades = db.scalars(select(DerivativePosition).where(DerivativePosition.status == "OPEN")).all()
        if trades and all(Decimal(x.market_value_reporting_ccy) == 0 for x in trades):
            findings.append(AgentFinding(
                agent=self.name,
                severity="HIGH",
                title="Derivative valuation challenge",
                message="All open derivatives have zero MTM; verify that market valuation data is being ingested before relying on counterparty or settlement risk.",
            ))
        return findings
