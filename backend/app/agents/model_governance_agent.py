from sqlalchemy.orm import Session
from app.agents.base import TreasuryAgent
from app.schemas.treasury import AgentFinding
from app.services.advanced_intelligence import payment_model_drift, validate_payment_model

class ModelGovernanceAgent(TreasuryAgent):
    name = "Model Governance & Drift Agent"
    def run(self, db: Session) -> list[AgentFinding]:
        v=validate_payment_model(db); d=payment_model_drift(db)
        sev="HIGH" if v.validation_status=="FAIL" or d.status=="HIGH" else "MEDIUM" if v.validation_status=="WATCH" or d.status=="WATCH" else "INFO"
        return [AgentFinding(agent=self.name,severity=sev,title="Model validation and drift status",message=f"Payment model validation={v.validation_status}; behavioural drift={d.status}.",metric=f"PSI {d.delay_psi}; MAE {v.mae_delay_days} days")]
