from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.agents.base import TreasuryAgent
from app.models import AuditLog
from app.schemas.treasury import AgentFinding


class AuditAgent(TreasuryAgent):
    name = "Audit & Traceability Agent"

    def run(self, db: Session) -> list[AgentFinding]:
        count = db.scalar(select(func.count(AuditLog.id))) or 0
        if count == 0:
            return [AgentFinding(
                agent=self.name,
                severity="INFO",
                title="Audit trail initialized",
                message="No prior treasury decision events exist yet; agent runs and market-data updates will be logged from this point forward.",
            )]
        return []
