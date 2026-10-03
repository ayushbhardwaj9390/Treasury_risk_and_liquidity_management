from sqlalchemy.orm import Session
from app.agents.base import TreasuryAgent
from app.schemas.treasury import AgentFinding
from app.services.advanced_intelligence import independent_price_verification

class IndependentPriceVerificationAgent(TreasuryAgent):
    name = "Independent Price Verification Agent"
    def run(self, db: Session) -> list[AgentFinding]:
        x=independent_price_verification(db)
        sev="HIGH" if x.fail_count or x.missing_count else "MEDIUM" if x.warning_count else "INFO"
        return [AgentFinding(agent=self.name,severity=sev,title="Derivative IPV control",message=f"IPV results: {x.pass_count} pass, {x.warning_count} warning, {x.fail_count} fail, {x.missing_count} missing.",metric=f"{x.fail_count+x.missing_count} escalation item(s)")]
