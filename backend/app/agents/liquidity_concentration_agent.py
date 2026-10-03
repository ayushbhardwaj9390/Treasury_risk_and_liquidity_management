from sqlalchemy.orm import Session
from app.agents.base import TreasuryAgent
from app.schemas.treasury import AgentFinding
from app.services.mvp13_liquidity_intelligence import calculate_liquidity_concentration

class LiquidityConcentrationAgent(TreasuryAgent):
    name = "Liquidity Concentration Agent"
    def run(self, db: Session) -> list[AgentFinding]:
        x = calculate_liquidity_concentration(db)
        max_share = max((r.top_share for r in x.rows), default=0)
        ms = float(max_share); ts = float(x.trapped_cash_share)
        sev = "HIGH" if ms >= 0.50 or ts >= 0.30 else "MEDIUM" if ms >= 0.40 or ts >= 0.20 else "INFO"
        return [AgentFinding(agent=self.name, severity=sev, title="Liquidity concentration and transferability", message=f"Max concentration={float(max_share):.1%}; trapped cash share={float(x.trapped_cash_share):.1%}; transferability ratio={float(x.transferability_ratio):.1%}.", metric=str(max_share))]
