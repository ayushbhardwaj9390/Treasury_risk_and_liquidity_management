from sqlalchemy.orm import Session
from app.agents.base import TreasuryAgent
from app.schemas.treasury import AgentFinding
from app.services.institutional_risk import calculate_legal_netting

class LegalNettingAgent(TreasuryAgent):
    name = "Legal Netting & Counterparty Agent"
    def run(self, db: Session) -> list[AgentFinding]:
        x = calculate_legal_netting(db)
        sev = "MEDIUM" if x.review_required_sets else "INFO"
        return [AgentFinding(agent=self.name, severity=sev, title="Legal netting recognition", message=f"{x.legally_enforceable_sets} netting set(s) recognized; {x.review_required_sets} set(s) require legal review and receive no netting benefit.", metric=f"Recognized netting benefit {x.total_netting_benefit} {x.reporting_currency}")]
