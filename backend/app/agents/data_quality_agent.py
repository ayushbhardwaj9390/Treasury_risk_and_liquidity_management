from datetime import UTC, datetime, timedelta
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.base import TreasuryAgent
from app.models import BankAccount, FXRate
from app.schemas.treasury import AgentFinding


class DataQualityAgent(TreasuryAgent):
    name = "Data Quality Agent"

    def run(self, db: Session) -> list[AgentFinding]:
        findings: list[AgentFinding] = []
        stale_cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=24)
        stale_accounts = db.scalars(select(BankAccount).where(BankAccount.last_updated < stale_cutoff)).all()
        if stale_accounts:
            findings.append(AgentFinding(
                agent=self.name,
                severity="HIGH",
                title="Stale bank balances",
                message=f"{len(stale_accounts)} bank account balance(s) are older than 24 hours.",
            ))

        rates = db.scalars(select(FXRate)).all()
        if not rates:
            findings.append(AgentFinding(
                agent=self.name,
                severity="CRITICAL",
                title="No FX market data",
                message="Group currency consolidation cannot be trusted until FX rates are loaded.",
            ))
        return findings
