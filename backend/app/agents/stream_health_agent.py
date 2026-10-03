from sqlalchemy.orm import Session
from app.agents.base import TreasuryAgent
from app.schemas.treasury import AgentFinding
from app.services.live_operations import live_operations_status


class StreamHealthAgent(TreasuryAgent):
    name = "Connector Stream Health Agent"

    def run(self, db: Session) -> list[AgentFinding]:
        s = live_operations_status(db)
        stale = [x for x in s.checkpoints if x.status != "ACTIVE" or (x.lag_seconds is not None and x.lag_seconds > 3600)]
        return [AgentFinding(
            agent=self.name,
            severity="HIGH" if stale else "INFO",
            title="Live connector checkpoints",
            message=f"Tracked streams={len(s.checkpoints)}; stale/degraded checkpoints={len(stale)}; duplicates={s.duplicate_events}.",
            metric=str(len(stale)),
        )]
