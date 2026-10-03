from sqlalchemy.orm import Session
from app.agents.base import TreasuryAgent
from app.schemas.treasury import AgentFinding
from app.services.treasury_optimization import optimize_funding

class CostOfLiquidityAgent(TreasuryAgent):
    name = "Cost of Liquidity Agent"
    def run(self, db: Session) -> list[AgentFinding]:
        x = optimize_funding(db)
        missing = sum(1 for r in x.rows if r.source_type == "COMMITTED_EXTERNAL_FACILITY" and r.cost_rate is None)
        sev = "MEDIUM" if missing else "INFO"
        return [AgentFinding(agent=self.name, severity=sev, title="Funding price completeness", message=f"{missing} committed external funding source(s) lack executable pricing inputs, so the engine does not claim a cheapest external source.", metric="Pricing completeness control")]
