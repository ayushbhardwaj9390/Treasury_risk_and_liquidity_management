from sqlalchemy.orm import Session

from app.agents.base import TreasuryAgent
from app.schemas.treasury import AgentFinding
from app.services.enterprise_controls import hedge_accounting_status


class HedgeAccountingAgent(TreasuryAgent):
    name = "Hedge Accounting Control Agent"

    def run(self, db: Session) -> list[AgentFinding]:
        rows = hedge_accounting_status(db)
        gaps = [x for x in rows if x.control_status != "READY"]
        if gaps:
            return [AgentFinding(
                agent=self.name,
                severity="MEDIUM",
                title="Hedge accounting documentation gap",
                message="One or more accounting hedge designations have incomplete documentation or effectiveness testing. Economic hedging may remain valid, but accounting treatment needs review.",
                metric=f"{len(gaps)} designations",
            )]
        return [AgentFinding(agent=self.name, severity="INFO", title="Hedge accounting controls ready", message="Configured hedge-accounting designations have complete documentation and passed effectiveness controls.")]
