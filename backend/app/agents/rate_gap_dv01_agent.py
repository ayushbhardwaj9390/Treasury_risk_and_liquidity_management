from sqlalchemy.orm import Session
from app.agents.base import TreasuryAgent
from app.schemas.treasury import AgentFinding
from app.services.mvp12_liquidity_command import calculate_interest_rate_gap_dv01

class RateGapDV01Agent(TreasuryAgent):
    name = "Interest Rate Gap & DV01 Agent"
    def run(self, db: Session) -> list[AgentFinding]:
        x = calculate_interest_rate_gap_dv01(db)
        sev = "HIGH" if x.residual_floating_reporting > x.fixed_debt_reporting else "MEDIUM" if x.residual_floating_reporting > 0 else "INFO"
        return [AgentFinding(agent=self.name, severity=sev, title="Rate-gap and DV01 profile", message=f"Residual floating exposure={x.residual_floating_reporting} {x.reporting_currency}; annual +100bp cash impact={x.annual_cash_impact_100bps}; combined DV01 proxy={x.combined_dv01_proxy_reporting}.", metric=str(x.annual_cash_impact_100bps))]
