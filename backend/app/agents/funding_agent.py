from datetime import date, timedelta
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.base import TreasuryAgent
from app.models import CreditFacility
from app.schemas.treasury import AgentFinding


class FundingAgent(TreasuryAgent):
    name = "Funding Agent"

    def run(self, db: Session) -> list[AgentFinding]:
        findings: list[AgentFinding] = []
        horizon = date.today() + timedelta(days=90)
        facilities = db.scalars(select(CreditFacility)).all()
        for f in facilities:
            utilization = Decimal(f.drawn_amount) / Decimal(f.limit_amount) if Decimal(f.limit_amount) else Decimal("0")
            if utilization >= Decimal("0.8"):
                findings.append(AgentFinding(
                    agent=self.name,
                    severity="HIGH",
                    title="High facility utilization",
                    message=f"{f.lender} facility utilization is at least 80%.",
                    metric=f"{utilization * 100:.1f}%",
                ))
            if f.maturity_date and f.maturity_date <= horizon:
                findings.append(AgentFinding(
                    agent=self.name,
                    severity="MEDIUM",
                    title="Facility maturity approaching",
                    message=f"{f.lender} facility matures within 90 days on {f.maturity_date.isoformat()}.",
                ))
        return findings
