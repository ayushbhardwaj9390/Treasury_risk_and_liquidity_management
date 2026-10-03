from decimal import Decimal
from sqlalchemy.orm import Session
from app.agents.base import TreasuryAgent
from app.schemas.treasury import AgentFinding
from app.services.institutional_risk import optimize_collateral_liquidity

class CollateralOptimizationAgent(TreasuryAgent):
    name = "Collateral Optimization Agent"
    def run(self, db: Session) -> list[AgentFinding]:
        x = optimize_collateral_liquidity(db)
        cross = Decimal(x.total_cross_currency_funding_required)
        sev = "HIGH" if cross > 0 else "MEDIUM" if Decimal(x.total_additional_collateral_required) > 0 else "INFO"
        return [AgentFinding(agent=self.name, severity=sev, title="Collateral funding optimization", message=f"Additional collateral requirement is {x.total_additional_collateral_required} {x.reporting_currency}; cross-currency funding requirement is {x.total_cross_currency_funding_required}.", metric=f"{len(x.rows)} active call(s)")]
