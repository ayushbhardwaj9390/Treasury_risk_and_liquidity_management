from sqlalchemy.orm import Session
from app.agents.base import TreasuryAgent
from app.schemas.treasury import AgentFinding
from app.services.advanced_intelligence import calculate_ml_cash_forecast, validate_payment_model

class MLForecastAgent(TreasuryAgent):
    name = "ML Cash Forecast Agent"
    def run(self, db: Session) -> list[AgentFinding]:
        v=validate_payment_model(db)
        f=calculate_ml_cash_forecast(db)
        sev="HIGH" if v.validation_status=="FAIL" else "MEDIUM" if v.validation_status in {"WATCH","INSUFFICIENT_DATA"} or f.first_conservative_breach_week else "INFO"
        title="ML forecast model requires review" if sev!="INFO" else "ML forecast confidence available"
        return [AgentFinding(agent=self.name,severity=sev,title=title,message=f"Payment timing model validation={v.validation_status}; conservative forecast breach week={f.first_conservative_breach_week}.",metric=f"Delay MAE {v.mae_delay_days} days") ]
