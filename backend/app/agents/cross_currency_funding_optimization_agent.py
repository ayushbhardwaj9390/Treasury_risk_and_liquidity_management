from sqlalchemy.orm import Session
from app.agents.base import TreasuryAgent
from app.schemas.treasury import AgentFinding
from app.services.mvp12_liquidity_command import analyze_cross_currency_funding

class CrossCurrencyFundingOptimizationAgent(TreasuryAgent):
    name = "Cross-Currency Funding Structuring Agent"
    def run(self, db: Session) -> list[AgentFinding]:
        x = analyze_cross_currency_funding(db)
        sev = "MEDIUM" if x.candidate_count else "INFO"
        return [AgentFinding(agent=self.name, severity=sev, title="Cross-currency funding candidates", message=f"{x.candidate_count} local deficit entities require structure comparison; decision status={x.decision_status}.", metric=str(x.candidate_count))]
