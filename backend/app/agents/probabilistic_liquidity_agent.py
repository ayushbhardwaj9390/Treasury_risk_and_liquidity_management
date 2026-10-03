from sqlalchemy.orm import Session
from app.agents.base import TreasuryAgent
from app.schemas.treasury import AgentFinding
from app.services.mvp13_liquidity_intelligence import calculate_probabilistic_liquidity_path

class ProbabilisticLiquidityAgent(TreasuryAgent):
    name = "Probabilistic Liquidity Path Agent"
    def run(self, db: Session) -> list[AgentFinding]:
        x = calculate_probabilistic_liquidity_path(db, simulations=1000)
        p = float(x.probability_of_any_buffer_breach)
        sev = "HIGH" if p >= 0.10 else "MEDIUM" if p >= 0.05 else "INFO"
        return [AgentFinding(agent=self.name, severity=sev, title="Probabilistic liquidity path", message=f"Any-buffer-breach probability={p:.1%}; 95% tail funding need={x.tail_funding_need_95}; median minimum headroom={x.median_minimum_headroom}.", metric=str(x.probability_of_any_buffer_breach))]
