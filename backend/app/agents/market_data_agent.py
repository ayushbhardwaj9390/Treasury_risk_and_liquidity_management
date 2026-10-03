from sqlalchemy.orm import Session

from app.agents.base import TreasuryAgent
from app.schemas.treasury import AgentFinding
from app.services.enterprise_controls import market_data_health


class MarketDataIntegrityAgent(TreasuryAgent):
    name = "Market Data Integrity Agent"

    def run(self, db: Session) -> list[AgentFinding]:
        findings: list[AgentFinding] = []
        rows = market_data_health(db)
        stale = [x for x in rows if x.stale]
        primary_unusable = [x for x in rows if x.source_type == "PRIMARY" and not x.execution_usable]
        if primary_unusable:
            findings.append(AgentFinding(agent=self.name, severity="HIGH", title="Primary market data unavailable", message="One or more primary market-data feeds are stale or inactive. Hedge execution should be blocked until an execution-usable primary feed is restored.", metric=f"{len(primary_unusable)} primary feeds"))
        elif stale:
            findings.append(AgentFinding(agent=self.name, severity="MEDIUM", title="Backup market feed stale", message="A non-primary market-data feed is outside its freshness tolerance. Primary execution feeds remain usable.", metric=f"{len(stale)} stale feeds"))
        else:
            findings.append(AgentFinding(agent=self.name, severity="INFO", title="Market data controls healthy", message="Required market-data feeds are within configured freshness tolerances."))
        return findings
