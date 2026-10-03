from sqlalchemy.orm import Session
from app.agents.base import TreasuryAgent
from app.schemas.treasury import AgentFinding
from app.services.mvp11_risk import optimize_digital_twin_scenarios

class DigitalTwinScenarioOptimizerAgent(TreasuryAgent):
    name = "Digital Twin Scenario Optimizer Agent"
    def run(self, db: Session) -> list[AgentFinding]:
        x = optimize_digital_twin_scenarios(db, fast_mode=True)
        top = x.scenarios[0] if x.scenarios else None
        sev = "MEDIUM" if top and top.limit_breach_count else "INFO"
        msg = f"Tested={x.combinations_tested}; execution={x.execution_authority}." if top is None else f"Tested={x.combinations_tested}; top score={top.resilience_score}; limit breaches={top.limit_breach_count}; execution={x.execution_authority}."
        return [AgentFinding(agent=self.name, severity=sev, title="Digital twin scenario optimization", message=msg, metric=str(top.resilience_score if top else 0))]
