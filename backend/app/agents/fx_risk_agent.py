from decimal import Decimal
from sqlalchemy.orm import Session

from app.agents.base import TreasuryAgent
from app.schemas.treasury import AgentFinding
from app.services.exposure import calculate_fx_exposures


class FXRiskAgent(TreasuryAgent):
    name = "FX Risk Agent"

    def run(self, db: Session) -> list[AgentFinding]:
        findings: list[AgentFinding] = []
        for row in calculate_fx_exposures(db):
            if abs(row.residual_exposure) > Decimal("10000000"):
                findings.append(AgentFinding(
                    agent=self.name,
                    severity="MEDIUM",
                    title=f"Material residual {row.currency} exposure",
                    message="Residual exposure exceeds the MVP materiality threshold and should be reviewed against hedge policy.",
                    metric=f"{row.residual_exposure:.2f} {row.currency}",
                ))
        return findings
