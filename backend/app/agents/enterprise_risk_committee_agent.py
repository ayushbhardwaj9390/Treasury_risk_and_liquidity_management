from sqlalchemy.orm import Session
from app.agents.base import TreasuryAgent
from app.schemas.treasury import AgentFinding
from app.services.digital_twin import run_digital_twin, calculate_market_risk_distribution

class EnterpriseRiskCommitteeAgent(TreasuryAgent):
    name = "Enterprise Treasury Risk Committee Agent"
    def run(self, db: Session) -> list[AgentFinding]:
        twin = run_digital_twin(db)
        market = calculate_market_risk_distribution(db, simulations=2000)
        sev = "HIGH" if twin.state == "STRESSED" else "MEDIUM" if twin.state == "WATCH" else "INFO"
        return [AgentFinding(agent=self.name, severity=sev, title="Integrated treasury risk committee view", message=f"Twin state={twin.state}; 95% LaR={twin.liquidity_at_risk_95}; FX expected shortfall={market.portfolio_expected_shortfall_95}; execution authority remains NONE.")]
