from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.base import TreasuryAgent
from app.models import TransactionProposal
from app.schemas.treasury import AgentFinding


class ExecutionControlAgent(TreasuryAgent):
    name = "Treasury Execution Control Agent"

    def run(self, db: Session) -> list[AgentFinding]:
        proposals = db.scalars(select(TransactionProposal)).all()
        blocked = [x for x in proposals if x.status == "CONTROL_FAILED" or x.control_status == "BLOCKED"]
        pending = [x for x in proposals if x.status in {"PENDING_APPROVAL", "PARTIALLY_APPROVED"}]
        released = [x for x in proposals if x.status == "RELEASED_FOR_EXECUTION"]
        findings: list[AgentFinding] = []
        if blocked:
            findings.append(AgentFinding(agent=self.name, severity="HIGH", title="Treasury transaction blocked", message="One or more proposed treasury transactions failed deterministic pre-trade controls and cannot proceed.", metric=f"{len(blocked)} blocked"))
        if pending:
            findings.append(AgentFinding(agent=self.name, severity="MEDIUM", title="Maker-checker approvals pending", message="Treasury transactions are awaiting independent approval under the maker-checker workflow.", metric=f"{len(pending)} pending"))
        if released:
            findings.append(AgentFinding(agent=self.name, severity="INFO", title="Transactions released to execution boundary", message="Approved transactions have been released to the external execution boundary. The AI layer does not autonomously move funds.", metric=f"{len(released)} released"))
        if not findings:
            findings.append(AgentFinding(agent=self.name, severity="INFO", title="No pending treasury execution items", message="No transaction proposal currently requires execution-control attention."))
        return findings
