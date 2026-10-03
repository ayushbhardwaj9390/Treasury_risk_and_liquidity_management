from sqlalchemy.orm import Session
from app.agents.base import TreasuryAgent
from app.schemas.treasury import AgentFinding
from app.services.digital_twin import run_digital_twin

class TreasuryDigitalTwinAgent(TreasuryAgent):
    name = "Treasury Digital Twin Agent"
    def run(self, db: Session) -> list[AgentFinding]:
        x = run_digital_twin(db)
        severity = "HIGH" if x.state == "STRESSED" else "MEDIUM" if x.state == "WATCH" else "INFO"
        return [AgentFinding(agent=self.name, severity=severity, title="Digital twin treasury state", message=f"State={x.state}; stressed headroom={x.scenario_stressed_headroom}; buffer breach probability={x.buffer_breach_probability}.", metric=str(x.scenario_stressed_headroom))]
