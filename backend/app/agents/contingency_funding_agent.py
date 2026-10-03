from sqlalchemy.orm import Session
from app.agents.base import TreasuryAgent
from app.schemas.treasury import AgentFinding
from app.services.mvp12_liquidity_command import build_contingency_funding_plan

class ContingencyFundingPlanAgent(TreasuryAgent):
    name = "Contingency Funding Plan Agent"
    def run(self, db: Session) -> list[AgentFinding]:
        x = build_contingency_funding_plan(db)
        sev = "CRITICAL" if x.status == "CRISIS" else "HIGH" if x.status == "ALERT" else "INFO"
        return [AgentFinding(agent=self.name, severity=sev, title="Contingency funding readiness", message=f"Status={x.status}; tail need={x.reference_tail_funding_need} {x.reporting_currency}; uncovered={x.uncovered_contingency_need}; survival={x.survival_horizon_days} days.", metric=str(x.uncovered_contingency_need))]
