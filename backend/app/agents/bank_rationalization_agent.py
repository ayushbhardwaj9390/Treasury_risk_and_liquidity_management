from sqlalchemy.orm import Session
from app.agents.base import TreasuryAgent
from app.schemas.treasury import AgentFinding
from app.services.digital_twin import calculate_bank_account_rationalization

class BankRationalizationAgent(TreasuryAgent):
    name = "Bank Account Rationalization Agent"
    def run(self, db: Session) -> list[AgentFinding]:
        x = calculate_bank_account_rationalization(db)
        findings=[]
        if x.stale_account_count:
            findings.append(AgentFinding(agent=self.name, severity="MEDIUM", title="Stale bank-account data", message=f"{x.stale_account_count} account(s) have balances older than 24 hours."))
        if x.review_candidate_count:
            findings.append(AgentFinding(agent=self.name, severity="INFO", title="Bank-account rationalization candidates", message=f"{x.review_candidate_count} low-utilization account(s) should be reviewed for operational necessity and fees."))
        if x.largest_bank_share > 0.35:
            findings.append(AgentFinding(agent=self.name, severity="MEDIUM", title="Bank cash concentration", message=f"Largest bank {x.largest_bank} holds {x.largest_bank_share} of modeled deployable cash.", metric=str(x.largest_bank_share)))
        return findings or [AgentFinding(agent=self.name, severity="INFO", title="Bank-account footprint", message="No material rationalization or concentration exception detected under current rules.")]
