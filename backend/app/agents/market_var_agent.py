from sqlalchemy.orm import Session
from app.agents.base import TreasuryAgent
from app.schemas.treasury import AgentFinding
from app.services.digital_twin import calculate_market_risk_distribution

class MarketVaREaRAgent(TreasuryAgent):
    name = "Market VaR & EaR Agent"
    def run(self, db: Session) -> list[AgentFinding]:
        x = calculate_market_risk_distribution(db, simulations=2000)
        sev = "MEDIUM" if x.portfolio_expected_shortfall_95 > 0 else "INFO"
        return [AgentFinding(agent=self.name, severity=sev, title="Residual market risk distribution", message=f"95% FX VaR={x.portfolio_var_95}; expected shortfall={x.portfolio_expected_shortfall_95}; 90-day EaR={x.earnings_at_risk_95_90d}.", metric=str(x.portfolio_var_95))]
