from sqlalchemy import select
from sqlalchemy.orm import Session
from app.agents.base import TreasuryAgent
from app.models import LiveTreasuryAlert
from app.schemas.treasury import AgentFinding


class ContinuousMonitorAgent(TreasuryAgent):
    name = "Continuous Treasury Monitoring Agent"

    def run(self, db: Session) -> list[AgentFinding]:
        rows = db.scalars(select(LiveTreasuryAlert).where(LiveTreasuryAlert.status.in_(["OPEN", "ACKNOWLEDGED"]))).all()
        critical = sum(1 for x in rows if x.severity == "CRITICAL")
        high = sum(1 for x in rows if x.severity == "HIGH")
        severity = "CRITICAL" if critical else "HIGH" if high else "INFO"
        return [AgentFinding(
            agent=self.name,
            severity=severity,
            title="Continuous treasury alert state",
            message=f"Open/acknowledged live alerts={len(rows)}; critical={critical}; high={high}. Monitoring is advisory and cannot execute treasury actions.",
            metric=str(len(rows)),
        )]
