from sqlalchemy.orm import Session
from app.agents.base import TreasuryAgent
from app.schemas.treasury import AgentFinding
from app.services.treasury_optimization import optimize_fx_hedges, optimize_funding

class TreasuryDecisionCommitteeAgent(TreasuryAgent):
    name = "Treasury Decision Committee Agent"
    def run(self, db: Session) -> list[AgentFinding]:
        h = optimize_fx_hedges(db)
        f = optimize_funding(db)
        return [AgentFinding(agent=self.name, severity="MEDIUM", title="Decision pack ready for human committee", message=f"Hedge and contingency-funding strategies are available for comparison. Modeled funding coverage is {f.covered_funding}/{f.requested_funding_need} {f.reporting_currency}; incremental hedge analysis totals {h.total_incremental_hedge_reporting} {h.reporting_currency}.", metric="No execution authority")]
