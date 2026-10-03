from sqlalchemy.orm import Session
from app.agents.base import TreasuryAgent
from app.schemas.treasury import AgentFinding
from app.services.mvp14_forecast_working_capital import calculate_forecast_accuracy


class ForecastAccuracyAgent(TreasuryAgent):
    name = "Forecast Accuracy & Bias Agent"

    def run(self, db: Session) -> list[AgentFinding]:
        x = calculate_forecast_accuracy(db)
        sev = "HIGH" if x.status == "FAIL" else "MEDIUM" if x.status == "WATCH" else "INFO"
        return [AgentFinding(
            agent=self.name,
            severity=sev,
            title="Cash forecast accuracy",
            message=f"WAPE={float(x.overall_wape):.1%}; cash bias={float(x.cash_bias_pct):.1%}; status={x.status}.",
            metric=str(x.overall_wape),
        )]
