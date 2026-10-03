from sqlalchemy.orm import Session
from app.agents.base import TreasuryAgent
from app.schemas.treasury import AgentFinding
from app.services.mvp13_liquidity_intelligence import calculate_forecast_driver_concentration

class ForecastDriverConcentrationAgent(TreasuryAgent):
    name = "Forecast Driver Concentration Agent"
    def run(self, db: Session) -> list[AgentFinding]:
        x = calculate_forecast_driver_concentration(db)
        share = float(x.top_five_driver_share)
        sev = "HIGH" if share >= 0.70 else "MEDIUM" if share >= 0.50 else "INFO"
        return [AgentFinding(agent=self.name, severity=sev, title="Forecast driver concentration", message=f"Top-five projected cash-flow drivers represent {share:.1%} of modeled absolute flows.", metric=str(x.top_five_driver_share))]
