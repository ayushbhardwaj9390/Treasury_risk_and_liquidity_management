from sqlalchemy.orm import Session
from app.agents.base import TreasuryAgent
from app.schemas.treasury import AgentFinding
from app.services.mvp11_risk import calculate_xva_style_adjustments

class XVAAgent(TreasuryAgent):
    name = "Counterparty XVA Sensitivity Agent"
    def run(self, db: Session) -> list[AgentFinding]:
        x = calculate_xva_style_adjustments(db)
        review = sum(1 for r in x.rows if r.data_status != "APPROVED_INPUTS")
        sev = "HIGH" if review else "MEDIUM" if x.total_xva_style_adjustment > 0 else "INFO"
        return [AgentFinding(agent=self.name, severity=sev, title="Counterparty CVA/FVA-style sensitivity", message=f"CVA-style={x.cva_style_total}; FVA-style={x.fva_style_total}; input reviews={review}.", metric=str(x.total_xva_style_adjustment))]
