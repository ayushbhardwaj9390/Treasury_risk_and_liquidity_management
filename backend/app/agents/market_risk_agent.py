from decimal import Decimal

from sqlalchemy.orm import Session

from app.agents.base import TreasuryAgent
from app.schemas.treasury import AgentFinding
from app.services.market_stress import calculate_market_stress


class MarketRiskAgent(TreasuryAgent):
    name = "Market Risk Agent"

    def run(self, db: Session) -> list[AgentFinding]:
        stress = calculate_market_stress(db, Decimal("0.10"), 100)
        findings: list[AgentFinding] = []
        if stress.estimated_fx_adverse_change > Decimal("5000000"):
            findings.append(AgentFinding(
                agent=self.name,
                severity="MEDIUM",
                title="Material residual FX stress sensitivity",
                message="A 10% adverse FX shock produces a material value sensitivity after existing economic hedges.",
                metric=f"{stress.estimated_fx_adverse_change:.2f} {stress.reporting_currency}",
            ))
        if stress.combined_market_liquidity_call > Decimal("10000000"):
            findings.append(AgentFinding(
                agent=self.name,
                severity="MEDIUM",
                title="Market stress may consume liquidity",
                message="Combined FX sensitivity, rate sensitivity and near-term derivative settlement exposure should be considered alongside the liquidity buffer.",
                metric=f"{stress.combined_market_liquidity_call:.2f} {stress.reporting_currency}",
            ))
        return findings
