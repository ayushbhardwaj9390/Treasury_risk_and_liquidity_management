from sqlalchemy.orm import Session
from app.agents.base import TreasuryAgent
from app.schemas.treasury import AgentFinding, LiquidityAttributionRequest
from app.services.mvp13_liquidity_intelligence import calculate_liquidity_stress_attribution

class LiquidityStressAttributionAgent(TreasuryAgent):
    name = "Liquidity Stress Attribution Agent"
    def run(self, db: Session) -> list[AgentFinding]:
        x = calculate_liquidity_stress_attribution(db, LiquidityAttributionRequest())
        adverse = sorted(x.rows, key=lambda r: r.standalone_headroom_impact, reverse=True)
        top = adverse[0] if adverse else None
        sev = "HIGH" if x.stressed_headroom < 0 else "MEDIUM" if x.total_deterioration > 0 else "INFO"
        msg = f"Stress deterioration={x.total_deterioration}; stressed headroom={x.stressed_headroom}."
        if top:
            msg += f" Largest standalone driver={top.driver} ({top.standalone_headroom_impact})."
        return [AgentFinding(agent=self.name, severity=sev, title="Liquidity stress attribution", message=msg, metric=str(x.total_deterioration))]
