from decimal import Decimal

from sqlalchemy.orm import Session

from app.agents.base import TreasuryAgent
from app.schemas.treasury import AgentFinding
from app.services.forecast import calculate_liquidity_forecast
from app.services.market_stress import calculate_market_stress


class StressAgent(TreasuryAgent):
    name = "Integrated Stress Agent"

    def run(self, db: Session) -> list[AgentFinding]:
        liquidity = calculate_liquidity_forecast(db, "SEVERE")
        market = calculate_market_stress(db, Decimal("0.10"), 200)
        findings: list[AgentFinding] = []

        if liquidity.first_buffer_breach_week is not None:
            findings.append(AgentFinding(
                agent=self.name,
                severity="HIGH",
                title="Severe liquidity stress breach",
                message=(
                    f"The severe 13-week operating stress breaches the configured buffer in week "
                    f"{liquidity.first_buffer_breach_week}. Market-risk liquidity demands should be held as an additional overlay."
                ),
                metric=f"Operating shortfall {liquidity.maximum_shortfall:.2f} {liquidity.reporting_currency}",
            ))
        if market.combined_market_liquidity_call > Decimal("0"):
            findings.append(AgentFinding(
                agent=self.name,
                severity="INFO",
                title="Market-risk liquidity overlay quantified",
                message="The market stress engine separately quantifies FX, rates and derivative-settlement liquidity pressure; it is not double-counted into the operating forecast.",
                metric=f"{market.combined_market_liquidity_call:.2f} {market.reporting_currency}",
            ))
        return findings
