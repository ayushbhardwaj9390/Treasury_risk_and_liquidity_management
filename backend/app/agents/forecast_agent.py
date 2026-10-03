from sqlalchemy.orm import Session

from app.agents.base import TreasuryAgent
from app.schemas.treasury import AgentFinding
from app.services.forecast import calculate_liquidity_forecast


class ForecastAgent(TreasuryAgent):
    name = "Liquidity Forecast Agent"

    def run(self, db: Session) -> list[AgentFinding]:
        findings: list[AgentFinding] = []
        base = calculate_liquidity_forecast(db, "BASE")
        severe = calculate_liquidity_forecast(db, "SEVERE")

        if base.first_buffer_breach_week is not None:
            findings.append(AgentFinding(
                agent=self.name,
                severity="HIGH",
                title="Base-case liquidity buffer breach",
                message=f"Base forecast falls below the required liquidity buffer in week {base.first_buffer_breach_week}.",
                metric=f"Maximum shortfall {base.maximum_shortfall} {base.reporting_currency}",
            ))
        elif severe.first_buffer_breach_week is not None:
            findings.append(AgentFinding(
                agent=self.name,
                severity="MEDIUM",
                title="Stress liquidity vulnerability",
                message=f"Severe stress breaches the required liquidity buffer in week {severe.first_buffer_breach_week}; base case remains above buffer.",
                metric=f"Stress shortfall {severe.maximum_shortfall} {severe.reporting_currency}",
            ))
        else:
            findings.append(AgentFinding(
                agent=self.name,
                severity="INFO",
                title="13-week liquidity buffer maintained",
                message="Base and severe synthetic scenarios remain above the required group liquidity buffer throughout the forecast horizon.",
                metric=f"Base ending headroom {base.ending_liquidity_headroom} {base.reporting_currency}",
            ))
        return findings
