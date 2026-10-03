from sqlalchemy.orm import Session
from app.agents.base import TreasuryAgent
from app.schemas.treasury import AgentFinding
from app.services.advanced_intelligence import calculate_intraday_liquidity

class IntradayLiquidityAgent(TreasuryAgent):
    name = "Intraday Liquidity Agent"
    def run(self, db: Session) -> list[AgentFinding]:
        x=calculate_intraday_liquidity(db)
        if x.first_buffer_breach_bucket:
            return [AgentFinding(agent=self.name,severity="HIGH",title="Intraday liquidity buffer breach",message=f"Projected intraday liquidity falls below the approved buffer during {x.first_buffer_breach_bucket}.",metric=f"Peak funding need {x.peak_intraday_funding_need} {x.reporting_currency}")]
        return [AgentFinding(agent=self.name,severity="INFO",title="Intraday liquidity buffer maintained",message="Scheduled intraday flows remain within cash and committed-facility capacity.")]
