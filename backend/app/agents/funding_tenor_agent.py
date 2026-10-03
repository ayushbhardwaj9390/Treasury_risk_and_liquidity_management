from sqlalchemy.orm import Session
from app.agents.base import TreasuryAgent
from app.schemas.treasury import AgentFinding
from app.services.mvp12_liquidity_command import optimize_funding_tenor

class FundingTenorAgent(TreasuryAgent):
    name = "Funding Tenor Optimization Agent"
    def run(self, db: Session) -> list[AgentFinding]:
        x = optimize_funding_tenor(db)
        sev = "MEDIUM" if x.current_top_lender_share >= 0.40 or x.current_funding_due_180d > 0 else "INFO"
        long_share = next((r.target_share for r in x.rows if r.tenor_bucket == ">3Y"), 0)
        return [AgentFinding(agent=self.name, severity=sev, title="Funding tenor resilience", message=f"New funding need={x.requested_new_funding} {x.reporting_currency}; suggested >3Y share={long_share}; top-lender share={x.current_top_lender_share}.", metric=str(x.requested_new_funding))]
