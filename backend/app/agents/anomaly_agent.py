from sqlalchemy.orm import Session
from app.agents.base import TreasuryAgent
from app.schemas.treasury import AgentFinding
from app.services.advanced_intelligence import detect_payment_anomalies

class PaymentAnomalyAgent(TreasuryAgent):
    name = "Treasury Anomaly Detection Agent"
    def run(self, db: Session) -> list[AgentFinding]:
        x=detect_payment_anomalies(db)
        if x:
            return [AgentFinding(agent=self.name,severity="HIGH" if any(a.severity=="HIGH" for a in x) else "MEDIUM",title="Unusual intraday payment pattern",message=f"{len(x)} payment(s) are anomalous versus historical payment behaviour and require review before release.",metric=x[0].payment_reference)]
        return [AgentFinding(agent=self.name,severity="INFO",title="No material payment anomaly",message="No scheduled payment crossed the anomaly-review threshold.")]
