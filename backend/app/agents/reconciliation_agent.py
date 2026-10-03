from sqlalchemy.orm import Session

from app.agents.base import TreasuryAgent
from app.schemas.treasury import AgentFinding
from app.services.enterprise_controls import connector_health, latest_reconciliations


class ReconciliationAgent(TreasuryAgent):
    name = "Treasury Reconciliation Agent"

    def run(self, db: Session) -> list[AgentFinding]:
        findings: list[AgentFinding] = []
        bad_connectors = [x for x in connector_health(db) if not x.execution_usable]
        failed = [x for x in latest_reconciliations(db) if x.status == "FAIL"]
        warnings = [x for x in latest_reconciliations(db) if x.status == "WARN"]
        if bad_connectors:
            findings.append(AgentFinding(agent=self.name, severity="HIGH", title="Treasury source connector stale", message="Required bank/ERP information may no longer be execution-grade. Transaction release should remain blocked for affected flows.", metric=f"{len(bad_connectors)} connectors"))
        if failed:
            findings.append(AgentFinding(agent=self.name, severity="HIGH", title="Reconciliation failure", message="A treasury reconciliation failed. Unresolved source-to-ledger differences must be cleared before transaction release.", metric=f"{len(failed)} failed runs"))
        elif warnings:
            findings.append(AgentFinding(agent=self.name, severity="MEDIUM", title="Reconciliation exceptions", message="Treasury reconciliation contains unmatched items requiring operational review, although no hard failure is present.", metric=f"{sum(x.unmatched_count for x in warnings)} unmatched"))
        if not findings:
            findings.append(AgentFinding(agent=self.name, severity="INFO", title="Reconciliation controls healthy", message="Required connectors and latest reconciliation controls are execution-usable."))
        return findings
