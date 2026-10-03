from decimal import Decimal
from sqlalchemy.orm import Session
from app.agents.base import TreasuryAgent
from app.schemas.treasury import AgentFinding, IntegratedScenarioRequest
from app.services.integrated_scenario import calculate_integrated_scenario

class ScenarioOrchestrationAgent(TreasuryAgent):
    name = "Integrated Scenario Orchestration Agent"
    def run(self, db: Session) -> list[AgentFinding]:
        x=calculate_integrated_scenario(db, IntegratedScenarioRequest(label="Agent combined stress", receivable_multiplier=Decimal("0.65"), payable_multiplier=Decimal("1.20"), facility_availability=Decimal("0.40"), fx_shock_pct=Decimal("0.15"), rate_shock_bps=300, collateral_stress_multiplier=Decimal("1.25"), refinancing_spread_shock_bps=250))
        sev="HIGH" if x.status=="BREACH" else "MEDIUM" if x.status=="WATCH" else "INFO"
        return [AgentFinding(agent=self.name,severity=sev,title="Combined treasury stress",message=f"Integrated liquidity + rates + collateral + refinancing scenario status is {x.status}.",metric=f"Stressed headroom {x.stressed_liquidity_headroom_after_overlays} {x.reporting_currency}")]
