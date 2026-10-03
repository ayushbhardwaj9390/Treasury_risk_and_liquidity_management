from decimal import Decimal
from sqlalchemy.orm import Session
from app.agents.base import TreasuryAgent
from app.schemas.treasury import AgentFinding
from app.services.treasury_optimization import optimize_fx_hedges

class HedgeOptimizationAgent(TreasuryAgent):
    name = "Portfolio Hedge Optimization Agent"
    def run(self, db: Session) -> list[AgentFinding]:
        x = optimize_fx_hedges(db)
        add = Decimal(x.total_incremental_hedge_reporting)
        exceptions = sum(1 for r in x.rows if r.status not in {"FEASIBLE", "POLICY_CONSTRAINED"})
        sev = "HIGH" if exceptions else "MEDIUM" if add > 0 else "INFO"
        return [AgentFinding(agent=self.name, severity=sev, title="Portfolio hedge optimization", message=f"Policy-constrained hedge analysis identifies {add} {x.reporting_currency} of incremental hedge notional at the configured target, with {exceptions} mapping exception(s).", metric=f"Illustrative execution-liquidity cost {x.estimated_execution_liquidity_cost_reporting} {x.reporting_currency}")]
