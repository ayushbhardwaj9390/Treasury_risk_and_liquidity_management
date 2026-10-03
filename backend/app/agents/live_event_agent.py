from sqlalchemy.orm import Session
from app.agents.base import TreasuryAgent
from app.schemas.treasury import AgentFinding
from app.services.live_operations import live_operations_status


class LiveEventIntegrityAgent(TreasuryAgent):
    name = "Live Event Integrity Agent"

    def run(self, db: Session) -> list[AgentFinding]:
        s = live_operations_status(db)
        exception_count = s.failed_24h + s.quarantined_24h
        severity = "HIGH" if s.failed_24h else "MEDIUM" if s.quarantined_24h else "INFO"
        return [AgentFinding(
            agent=self.name,
            severity=severity,
            title="Treasury event-stream integrity",
            message=f"24h events={s.events_24h}; failed/quarantined={exception_count}; max arrival lag={s.max_event_lag_seconds}s.",
            metric=s.status,
        )]
