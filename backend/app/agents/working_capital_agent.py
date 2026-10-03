from sqlalchemy.orm import Session
from app.agents.base import TreasuryAgent
from app.schemas.treasury import AgentFinding
from app.services.mvp14_forecast_working_capital import calculate_working_capital_cycle


class WorkingCapitalCycleAgent(TreasuryAgent):
    name = "Working Capital Cycle Agent"

    def run(self, db: Session) -> list[AgentFinding]:
        x = calculate_working_capital_cycle(db)
        change = float(x.group_ccc_change_days or 0)
        sev = "HIGH" if change >= 5 else "MEDIUM" if change >= 2 else "INFO"
        return [AgentFinding(
            agent=self.name,
            severity=sev,
            title="Cash conversion cycle",
            message=f"Group DSO={x.group_dso_days}d, DPO={x.group_dpo_days}d, DIO={x.group_dio_days}d, CCC={x.group_ccc_days}d; latest change={x.group_ccc_change_days or 0}d.",
            metric=str(x.group_ccc_days),
        )]
