from sqlalchemy.orm import Session
from app.agents.base import TreasuryAgent
from app.schemas.treasury import AgentFinding
from app.services.mvp11_risk import calculate_funding_concentration

class FundingConcentrationAgent(TreasuryAgent):
    name = "Funding Concentration Agent"
    def run(self, db: Session) -> list[AgentFinding]:
        x = calculate_funding_concentration(db)
        sev = "HIGH" if x.top_lender_share > 0.45 or x.hhi > 0.25 else "MEDIUM" if x.top_lender_share > 0.35 else "INFO"
        return [AgentFinding(agent=self.name, severity=sev, title="Funding concentration", message=f"Top lender={x.top_lender}; share={x.top_lender_share}; HHI={x.hhi}; due180={x.funding_due_180d}.", metric=str(x.top_lender_share))]
