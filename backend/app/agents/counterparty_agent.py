from sqlalchemy.orm import Session

from app.agents.base import TreasuryAgent
from app.schemas.treasury import AgentFinding
from app.services.derivative_risk import calculate_counterparty_exposure


class CounterpartyAgent(TreasuryAgent):
    name = "Counterparty Risk Agent"

    def run(self, db: Session) -> list[AgentFinding]:
        findings: list[AgentFinding] = []
        for row in calculate_counterparty_exposure(db):
            if row.status == "BREACH":
                findings.append(AgentFinding(
                    agent=self.name,
                    severity="HIGH",
                    title="Counterparty limit breached",
                    message=f"Derivative credit exposure to {row.counterparty} exceeds its configured limit.",
                    metric=f"{row.utilization * 100:.1f}% utilized",
                ))
            elif row.status == "WARNING":
                findings.append(AgentFinding(
                    agent=self.name,
                    severity="MEDIUM",
                    title="Counterparty limit nearing capacity",
                    message=f"Derivative credit exposure to {row.counterparty} has entered the warning zone.",
                    metric=f"{row.utilization * 100:.1f}% utilized",
                ))
            elif row.status == "NO-LIMIT":
                findings.append(AgentFinding(
                    agent=self.name,
                    severity="HIGH",
                    title="Missing counterparty limit",
                    message=f"No approved derivative exposure limit is configured for {row.counterparty}.",
                ))
        return findings
