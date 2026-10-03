from decimal import Decimal
from sqlalchemy.orm import Session

from app.agents.base import TreasuryAgent
from app.schemas.treasury import AgentFinding
from app.services.liquidity import calculate_global_liquidity


class LiquidityAgent(TreasuryAgent):
    name = "Liquidity Agent"

    def run(self, db: Session) -> list[AgentFinding]:
        liq = calculate_global_liquidity(db)
        findings: list[AgentFinding] = []

        if liq.liquidity_headroom < 0:
            findings.append(AgentFinding(
                agent=self.name,
                severity="CRITICAL",
                title="Group liquidity buffer breached",
                message="Deployable cash plus committed undrawn facilities are below minimum group cash requirements.",
                metric=f"{liq.liquidity_headroom:.2f} {liq.reporting_currency}",
            ))
        else:
            findings.append(AgentFinding(
                agent=self.name,
                severity="INFO",
                title="Group liquidity headroom available",
                message="Current consolidated liquidity remains above the configured minimum cash requirement.",
                metric=f"{liq.liquidity_headroom:.2f} {liq.reporting_currency}",
            ))

        negative_entities = [e.entity_name for e in liq.entities if e.liquidity_headroom_reporting < Decimal("0")]
        if negative_entities:
            findings.append(AgentFinding(
                agent=self.name,
                severity="HIGH",
                title="Local liquidity deficit detected",
                message="Entities below local minimum liquidity: " + ", ".join(negative_entities),
            ))
        return findings
