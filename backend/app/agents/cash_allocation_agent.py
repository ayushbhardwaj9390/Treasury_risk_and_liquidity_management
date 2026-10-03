from sqlalchemy.orm import Session
from app.agents.base import TreasuryAgent
from app.schemas.treasury import AgentFinding
from app.services.treasury_optimization import optimize_cash_pool

class CashAllocationOptimizationAgent(TreasuryAgent):
    name = "Cash Allocation Optimization Agent"
    def run(self, db: Session) -> list[AgentFinding]:
        x = optimize_cash_pool(db)
        return [AgentFinding(agent=self.name, severity="MEDIUM" if x.instruction_count else "INFO", title="Cash-pool internal offset", message=f"Cash-pool analysis identifies {x.total_internal_offset} of same-pool internal funding offset across {x.instruction_count} proposed sweep(s).", metric="Analytical proposals only")]
