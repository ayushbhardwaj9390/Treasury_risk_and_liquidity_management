from sqlalchemy.orm import Session
from app.agents.base import TreasuryAgent
from app.schemas.treasury import AgentFinding
from app.services.institutional_risk import champion_challenger_analysis

class ChampionChallengerAgent(TreasuryAgent):
    name = "Champion-Challenger Model Agent"
    def run(self, db: Session) -> list[AgentFinding]:
        x = champion_challenger_analysis(db)
        sev = "MEDIUM" if x.recommendation == "INDEPENDENT_VALIDATION_FOR_PROMOTION" else "INFO"
        return [AgentFinding(agent=self.name, severity=sev, title="Champion/challenger governance", message=f"Recommendation={x.recommendation}. Auto-promotion remains disabled regardless of model performance.", metric=f"MAE improvement {float(x.mae_improvement_pct)*100:.2f}%")]
