from sqlalchemy.orm import Session
from app.agents.base import TreasuryAgent
from app.schemas.treasury import AgentFinding
from app.services.mvp12_liquidity_command import run_balance_sheet_twin

class BalanceSheetTwinAgent(TreasuryAgent):
    name = "Predictive Balance-Sheet Twin Agent"
    def run(self, db: Session) -> list[AgentFinding]:
        x = run_balance_sheet_twin(db)
        sev = "CRITICAL" if x.status == "CRITICAL" else "MEDIUM" if x.status == "WATCH" else "INFO"
        return [AgentFinding(agent=self.name, severity=sev, title="Predictive balance-sheet treasury state", message=f"State={x.status}; stressed headroom={x.stressed_liquidity_headroom} {x.reporting_currency}; survival={x.survival_horizon_days} days; residual floating exposure={x.residual_floating_rate_exposure}.", metric=str(x.stressed_liquidity_headroom))]
