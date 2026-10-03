from decimal import Decimal
from sqlalchemy.orm import Session
from app.agents.base import TreasuryAgent
from app.schemas.treasury import AgentFinding
from app.services.treasury_optimization import optimize_funding

class FundingOptimizationAgent(TreasuryAgent):
    name = "Funding Optimization Agent"
    def run(self, db: Session) -> list[AgentFinding]:
        x = optimize_funding(db)
        uncovered = Decimal(x.uncovered_funding)
        sev = "HIGH" if uncovered > 0 else "MEDIUM"
        return [AgentFinding(agent=self.name, severity=sev, title="Tail-liquidity funding plan", message=f"The modeled tail funding need is {x.requested_funding_need} {x.reporting_currency}; {x.covered_funding} is covered by governed internal cash and committed external capacity.", metric=f"Uncovered {x.uncovered_funding} {x.reporting_currency}")]
