from sqlalchemy.orm import Session
from app.agents.base import TreasuryAgent
from app.schemas.treasury import AgentFinding
from app.services.mvp13_liquidity_intelligence import build_liquidity_action_playbook

class LiquidityActionPlaybookAgent(TreasuryAgent):
    name = "Liquidity Action Playbook Agent"
    def run(self, db: Session) -> list[AgentFinding]:
        x = build_liquidity_action_playbook(db)
        sev = "HIGH" if x.residual_uncovered_need > 0 else "MEDIUM" if x.trigger_status not in {"ADEQUATE", "READY"} else "INFO"
        return [AgentFinding(agent=self.name, severity=sev, title="Liquidity action playbook", message=f"Reference tail need={x.reference_tail_funding_need}; quantified modeled actions={x.quantified_capacity_total}; residual uncovered={x.residual_uncovered_need}. Execution authority remains NONE.", metric=str(x.residual_uncovered_need))]
