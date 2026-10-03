from sqlalchemy.orm import Session
from app.agents.base import TreasuryAgent
from app.schemas.treasury import AgentFinding
from app.services.global_treasury import calculate_refinancing_risk


class RefinancingAgent(TreasuryAgent):
    name = "Refinancing & Covenant Agent"

    def run(self, db: Session) -> list[AgentFinding]:
        risk = calculate_refinancing_risk(db)
        findings: list[AgentFinding] = []
        breaches = [c for c in risk.covenants if c.status == "BREACH"]
        watches = [c for c in risk.covenants if c.status == "WARNING"]
        if breaches:
            findings.append(AgentFinding(
                agent=self.name,
                severity="CRITICAL",
                title="Covenant breach",
                message=f"{len(breaches)} configured covenant test(s) are in breach; assess waiver, acceleration clauses and immediate liquidity consequences.",
            ))
        elif watches:
            findings.append(AgentFinding(
                agent=self.name,
                severity="HIGH",
                title="Covenant headroom narrowing",
                message=f"{len(watches)} covenant test(s) are inside the configured warning buffer.",
            ))
        if risk.debt_due_180d > 0:
            findings.append(AgentFinding(
                agent=self.name,
                severity="MEDIUM",
                title="Near-term refinancing requirement",
                message=f"Debt of {risk.reporting_currency} {risk.debt_due_180d:,.0f} matures within 180 days.",
                metric=str(risk.debt_due_180d),
            ))
        if risk.committed_facilities_due_90d > 0:
            findings.append(AgentFinding(
                agent=self.name,
                severity="HIGH",
                title="Committed liquidity expiry",
                message=f"{risk.reporting_currency} {risk.committed_facilities_due_90d:,.0f} of currently undrawn committed capacity expires within 90 days.",
                metric=str(risk.committed_facilities_due_90d),
            ))
        return findings
