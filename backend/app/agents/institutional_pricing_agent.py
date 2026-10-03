from sqlalchemy.orm import Session
from app.agents.base import TreasuryAgent
from app.schemas.treasury import AgentFinding
from app.services.institutional_risk import calculate_institutional_valuation

class InstitutionalPricingAgent(TreasuryAgent):
    name = "Institutional Pricing & Valuation Agent"
    def run(self, db: Session) -> list[AgentFinding]:
        x = calculate_institutional_valuation(db)
        reviews = sum(1 for r in x.rows if r.model_status != "PASS")
        sev = "HIGH" if x.unpriced_trade_count else "MEDIUM" if reviews else "INFO"
        return [AgentFinding(agent=self.name, severity=sev, title="Independent model valuation layer", message=f"Priced {x.priced_trade_count} open derivatives with {x.unpriced_trade_count} unpriced and {reviews} model-value review item(s).", metric=f"Aggregate model/book difference {x.aggregate_difference} {x.reporting_currency}")]
