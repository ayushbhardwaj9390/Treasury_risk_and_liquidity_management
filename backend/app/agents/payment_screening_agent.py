from sqlalchemy.orm import Session
from app.agents.base import TreasuryAgent
from app.schemas.treasury import AgentFinding
from app.services.advanced_intelligence import payment_screening_status

class PaymentScreeningAgent(TreasuryAgent):
    name = "Payment Screening Control Agent"
    def run(self, db: Session) -> list[AgentFinding]:
        rows=payment_screening_status(db); blocked=[x for x in rows if x.execution_blocked]
        if blocked:
            return [AgentFinding(agent=self.name,severity="HIGH",title="Payment screening review required",message=f"{len(blocked)} payment screening case(s) are not cleared. Execution must remain blocked pending compliance disposition.",metric=blocked[0].payment_reference)]
        return [AgentFinding(agent=self.name,severity="INFO",title="Screened payments cleared",message="Available screening results contain no unresolved execution block.")]
