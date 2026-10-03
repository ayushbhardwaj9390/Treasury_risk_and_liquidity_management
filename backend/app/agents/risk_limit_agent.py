from sqlalchemy.orm import Session
from app.agents.base import TreasuryAgent
from app.schemas.treasury import AgentFinding
from app.services.mvp11_risk import evaluate_treasury_risk_limits

class TreasuryRiskLimitAgent(TreasuryAgent):
    name = "Treasury Risk Limit Framework Agent"
    def run(self, db: Session) -> list[AgentFinding]:
        x = evaluate_treasury_risk_limits(db, lar_simulations=500)
        sev = "HIGH" if x.breach_count else "MEDIUM" if x.warning_count else "INFO"
        return [AgentFinding(agent=self.name, severity=sev, title="Treasury risk limit framework", message=f"Status={x.overall_status}; breaches={x.breach_count}; warnings={x.warning_count}.", metric=str(x.breach_count))]
