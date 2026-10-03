from sqlalchemy.orm import Session
from app.agents.base import TreasuryAgent
from app.schemas.treasury import AgentFinding
from app.services.mvp12_liquidity_command import calculate_early_warning_indicators

class TreasuryEarlyWarningAgent(TreasuryAgent):
    name = "Treasury Early Warning Agent"
    def run(self, db: Session) -> list[AgentFinding]:
        x = calculate_early_warning_indicators(db)
        sev = "CRITICAL" if x.red_count else "MEDIUM" if x.amber_count else "INFO"
        return [AgentFinding(agent=self.name, severity=sev, title="Treasury early-warning indicators", message=f"Overall={x.overall_status}; red={x.red_count}; amber={x.amber_count}; governed limit status={x.governed_limit_status}.", metric=x.overall_status)]
