from decimal import Decimal
from sqlalchemy.orm import Session
from app.agents.base import TreasuryAgent
from app.schemas.treasury import AgentFinding
from app.services.treasury_optimization import search_treasury_scenarios

class ScenarioSearchAgent(TreasuryAgent):
    name = "Treasury Scenario Search Agent"
    def run(self, db: Session) -> list[AgentFinding]:
        x = search_treasury_scenarios(db, top_n=3, compact=True)
        sev = "HIGH" if x.breach_count else "INFO"
        return [AgentFinding(agent=self.name, severity=sev, title="Multi-factor scenario search", message=f"Compact scenario search tested {x.combinations_tested} combinations and found {x.breach_count} liquidity breach configuration(s).", metric=f"Worst headroom {x.worst_stressed_headroom} {x.reporting_currency}")]
