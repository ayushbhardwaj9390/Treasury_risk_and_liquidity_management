from sqlalchemy.orm import Session
from app.agents.base import TreasuryAgent
from app.schemas.treasury import AgentFinding
from app.services.digital_twin import calculate_liquidity_transfer_pricing

class LiquidityTransferPricingAgent(TreasuryAgent):
    name = "Liquidity Transfer Pricing Agent"
    def run(self, db: Session) -> list[AgentFinding]:
        x = calculate_liquidity_transfer_pricing(db)
        deficits = [r for r in x.rows if r.position_type == "DEFICIT"]
        if not deficits:
            return [AgentFinding(agent=self.name, severity="INFO", title="Internal liquidity pricing", message="No entity-level liquidity deficits require an internal scarcity charge in the current snapshot.")]
        return [AgentFinding(agent=self.name, severity="MEDIUM", title="Entity liquidity scarcity pricing", message=f"{len(deficits)} entity liquidity position(s) carry the internal deficit charge rate of {x.deficit_charge_rate}.", metric=str(x.deficit_charge_rate))]
