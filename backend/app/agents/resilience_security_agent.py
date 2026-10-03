from sqlalchemy.orm import Session
from app.agents.base import TreasuryAgent
from app.schemas.treasury import AgentFinding
from app.services.institutional_risk import operational_resilience_status, security_posture

class ResilienceSecurityAgent(TreasuryAgent):
    name = "Operational Resilience & Security Agent"
    def run(self, db: Session) -> list[AgentFinding]:
        r = operational_resilience_status(db)
        s = security_posture()
        findings = []
        findings.append(AgentFinding(agent=self.name, severity="HIGH" if r.tier1_gaps else "INFO", title="Treasury service resilience", message=f"Tier-1 resilience gaps={r.tier1_gaps} across {r.tier1_count} critical components.", metric=r.overall_status))
        findings.append(AgentFinding(agent=self.name, severity="MEDIUM" if s.status == "GAP" else "INFO", title="Identity and platform security posture", message=f"Environment={s.environment}; auth={s.auth_mode}; database={s.database_backend}.", metric=s.status))
        return findings
