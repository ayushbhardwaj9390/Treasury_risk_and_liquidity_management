from sqlalchemy.orm import Session
from app.agents.base import TreasuryAgent
from app.schemas.treasury import AgentFinding
from app.services.advanced_intelligence import predict_open_receivables

class PaymentBehaviorAgent(TreasuryAgent):
    name = "Payment Behaviour Agent"
    def run(self, db: Session) -> list[AgentFinding]:
        rows=predict_open_receivables(db)
        risky=[x for x in rows if x.late_probability >= 0.65 or x.expected_delay_days >= 10]
        if risky:
            return [AgentFinding(agent=self.name,severity="MEDIUM",title="Collection timing risk",message=f"{len(risky)} open receivable(s) show elevated late-payment risk based on payment behaviour history.",metric=f"Worst expected delay {max(x.expected_delay_days for x in risky)} days")]
        return [AgentFinding(agent=self.name,severity="INFO",title="Payment behaviour within tolerance",message="No open receivable has crossed the configured payment-delay warning threshold.")]
