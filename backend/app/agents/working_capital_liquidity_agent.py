from sqlalchemy.orm import Session
from app.agents.base import TreasuryAgent
from app.schemas.treasury import AgentFinding, WorkingCapitalLiquidityBridgeRequest
from app.services.mvp14_forecast_working_capital import calculate_working_capital_liquidity_bridge


class WorkingCapitalLiquidityAgent(TreasuryAgent):
    name = "Working Capital Liquidity Agent"

    def run(self, db: Session) -> list[AgentFinding]:
        x = calculate_working_capital_liquidity_bridge(db, WorkingCapitalLiquidityBridgeRequest())
        return [AgentFinding(
            agent=self.name,
            severity="INFO",
            title="Working-capital liquidity bridge",
            message=f"Illustrative modeled cash release={x.total_modeled_cash_release}; pro-forma headroom={x.pro_forma_liquidity_headroom}. Execution authority remains NONE.",
            metric=str(x.total_modeled_cash_release),
        )]
