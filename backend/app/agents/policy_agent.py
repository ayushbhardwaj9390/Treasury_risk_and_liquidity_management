from sqlalchemy.orm import Session

from app.agents.base import TreasuryAgent
from app.schemas.treasury import AgentFinding
from app.services.liquidity import calculate_global_liquidity


class PolicyAgent(TreasuryAgent):
    name = "Policy Agent"

    def run(self, db: Session) -> list[AgentFinding]:
        # MVP policy check: local minimum cash requirements must not be breached.
        liq = calculate_global_liquidity(db)
        breached = [e.entity_name for e in liq.entities if e.liquidity_headroom_reporting < 0]
        if breached:
            return [AgentFinding(
                agent=self.name,
                severity="HIGH",
                title="Minimum cash policy exception",
                message="Local liquidity policy breached by: " + ", ".join(breached),
            )]
        return []
