from decimal import Decimal
from sqlalchemy.orm import Session
from app.agents.base import TreasuryAgent
from app.schemas.treasury import AgentFinding
from app.services.institutional_risk import calculate_liquidity_at_risk

class LiquidityAtRiskAgent(TreasuryAgent):
    name = "Liquidity-at-Risk Agent"
    def run(self, db: Session) -> list[AgentFinding]:
        x = calculate_liquidity_at_risk(db, simulations=1500)
        p = Decimal(x.probability_of_buffer_breach)
        sev = "HIGH" if p >= Decimal("0.10") else "MEDIUM" if p >= Decimal("0.03") else "INFO"
        return [AgentFinding(agent=self.name, severity=sev, title="Probabilistic liquidity tail", message=f"13-week simulated buffer-breach probability is {(p*100):.2f}% at the configured distribution assumptions.", metric=f"95% LaR {x.liquidity_at_risk} {x.reporting_currency}")]
