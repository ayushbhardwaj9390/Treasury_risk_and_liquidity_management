from decimal import Decimal
from sqlalchemy.orm import Session

from app.agents.base import TreasuryAgent
from app.schemas.treasury import AgentFinding
from app.services.derivative_risk import calculate_interest_rate_risk


class InterestRateAgent(TreasuryAgent):
    name = "Interest Rate Risk Agent"

    def run(self, db: Session) -> list[AgentFinding]:
        risk = calculate_interest_rate_risk(db)
        findings: list[AgentFinding] = []
        if risk.floating_share_after_hedges > Decimal("0.50"):
            findings.append(AgentFinding(
                agent=self.name,
                severity="MEDIUM",
                title="High residual floating-rate exposure",
                message="More than half of group debt remains economically exposed to floating rates after pay-fixed hedges.",
                metric=f"{risk.floating_share_after_hedges * 100:.1f}% floating after hedges",
            ))
        if risk.annual_cash_impact_100bps > Decimal("500000"):
            findings.append(AgentFinding(
                agent=self.name,
                severity="MEDIUM",
                title="Material rate-shock cash sensitivity",
                message="A parallel +100 bps shock would create a material annualized cash-interest increase on residual floating debt.",
                metric=f"{risk.annual_cash_impact_100bps:.2f} {risk.reporting_currency}",
            ))
        return findings
