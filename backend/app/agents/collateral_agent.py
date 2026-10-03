from sqlalchemy.orm import Session
from app.agents.base import TreasuryAgent
from app.schemas.treasury import AgentFinding
from app.services.global_treasury import calculate_collateral_liquidity


class CollateralAgent(TreasuryAgent):
    name = "Collateral & CSA Agent"

    def run(self, db: Session) -> list[AgentFinding]:
        risk = calculate_collateral_liquidity(db)
        findings: list[AgentFinding] = []
        if risk.current_margin_call > 0:
            findings.append(AgentFinding(
                agent=self.name,
                severity="HIGH",
                title="Current collateral liquidity call",
                message=f"Configured CSA terms imply a current collateral call of {risk.reporting_currency} {risk.current_margin_call:,.0f}.",
                metric=str(risk.current_margin_call),
            ))
        if risk.stressed_margin_call > risk.current_margin_call:
            findings.append(AgentFinding(
                agent=self.name,
                severity="MEDIUM",
                title="Collateral stress buffer required",
                message=f"Stressed collateral requirement rises to {risk.reporting_currency} {risk.stressed_margin_call:,.0f}; reserve this separately from operating forecast headroom.",
                metric=str(risk.stressed_margin_call),
            ))
        if risk.warnings:
            for warning in risk.warnings:
                if "no active CSA" in warning:
                    findings.append(AgentFinding(agent=self.name, severity="HIGH", title="CSA configuration gap", message=warning))
        return findings
