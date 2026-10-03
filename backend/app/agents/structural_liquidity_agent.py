from sqlalchemy.orm import Session
from app.agents.base import TreasuryAgent
from app.schemas.treasury import AgentFinding
from app.services.mvp12_liquidity_command import calculate_structural_liquidity_gap

class StructuralLiquidityAgent(TreasuryAgent):
    name = "Structural Liquidity Gap Agent"
    def run(self, db: Session) -> list[AgentFinding]:
        x = calculate_structural_liquidity_gap(db)
        floor = x.minimum_cumulative_cash_before_facilities
        sev = "HIGH" if floor < x.minimum_cash_buffer else "MEDIUM" if any(r.net_contractual_gap < 0 for r in x.rows[:4]) else "INFO"
        return [AgentFinding(agent=self.name, severity=sev, title="Structural liquidity ladder", message=f"Minimum cumulative contractual cash before facilities={floor} {x.reporting_currency}; minimum cash buffer={x.minimum_cash_buffer}.", metric=str(floor))]
