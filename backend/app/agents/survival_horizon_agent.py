from sqlalchemy.orm import Session
from app.agents.base import TreasuryAgent
from app.schemas.treasury import AgentFinding
from app.services.mvp11_risk import calculate_liquidity_survival_horizon

class LiquiditySurvivalHorizonAgent(TreasuryAgent):
    name = "Liquidity Survival Horizon Agent"
    def run(self, db: Session) -> list[AgentFinding]:
        x = calculate_liquidity_survival_horizon(db)
        sev = "CRITICAL" if x.status == "CRITICAL" else "HIGH" if x.status == "BREACH" else "INFO"
        return [AgentFinding(agent=self.name, severity=sev, title="Liquidity survival horizon", message=f"Survival={x.survival_horizon_days} days; first buffer breach={x.first_buffer_breach_week}; status={x.status}.", metric=str(x.survival_horizon_days))]
