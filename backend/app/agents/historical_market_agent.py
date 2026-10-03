from sqlalchemy.orm import Session
from app.agents.base import TreasuryAgent
from app.schemas.treasury import AgentFinding
from app.services.mvp11_risk import calculate_historical_market_risk

class HistoricalMarketCalibrationAgent(TreasuryAgent):
    name = "Historical Market Calibration Agent"
    def run(self, db: Session) -> list[AgentFinding]:
        x = calculate_historical_market_risk(db)
        sev = "MEDIUM" if x.portfolio_var > 0 else "INFO"
        return [AgentFinding(agent=self.name, severity=sev, title="Historically calibrated FX risk", message=f"10-day VaR={x.portfolio_var}; ES={x.expected_shortfall}; method={x.correlation_method}.", metric=str(x.portfolio_var))]
