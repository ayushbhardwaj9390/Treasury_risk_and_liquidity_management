from sqlalchemy.orm import Session
from app.agents.base import TreasuryAgent
from app.schemas.treasury import AgentFinding
from app.services.live_operations import list_execution_messages


class ExecutionMessagingAgent(TreasuryAgent):
    name = "Execution Messaging & Acknowledgement Agent"

    def run(self, db: Session) -> list[AgentFinding]:
        rows = list_execution_messages(db)
        pending = [x for x in rows if x.status in {"QUEUED", "SENT"}]
        rejected = [x for x in rows if x.status == "REJECTED"]
        severity = "HIGH" if rejected else "MEDIUM" if pending else "INFO"
        return [AgentFinding(
            agent=self.name,
            severity=severity,
            title="External execution acknowledgements",
            message=f"Execution messages={len(rows)}; pending acknowledgement={len(pending)}; rejected={len(rejected)}.",
            metric=str(len(pending)),
        )]
