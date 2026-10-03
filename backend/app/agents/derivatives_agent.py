from decimal import Decimal
from sqlalchemy.orm import Session

from app.agents.base import TreasuryAgent
from app.schemas.treasury import AgentFinding
from app.services.derivative_risk import calculate_hedge_coverage, derivative_risk_summary


class DerivativesAgent(TreasuryAgent):
    name = "Derivatives & Hedge Agent"

    def run(self, db: Session) -> list[AgentFinding]:
        findings: list[AgentFinding] = []
        summary = derivative_risk_summary(db)

        if summary.unmapped_trade_count:
            findings.append(AgentFinding(
                agent=self.name,
                severity="HIGH",
                title="Unmapped derivative position",
                message=f"{summary.unmapped_trade_count} open derivative trade(s) are not linked to an approved underlying exposure.",
            ))

        near_term = next((x for x in summary.maturity_buckets if x.bucket == "0-30d"), None)
        if near_term and near_term.trade_count:
            findings.append(AgentFinding(
                agent=self.name,
                severity="MEDIUM",
                title="Derivative settlements approaching",
                message=f"{near_term.trade_count} derivative trade(s) mature within 30 days; settlement liquidity and rollover decisions should be reviewed.",
                metric=f"{near_term.notional_reporting:.2f} {summary.reporting_currency} notional",
            ))

        for row in calculate_hedge_coverage(db):
            if row.status in {"UNDER-HEDGED", "OVER-HEDGED", "ABOVE-POLICY", "UNMATCHED"} and abs(row.underlying_exposure) + abs(row.hedge_notional) > Decimal("1000000"):
                severity = "HIGH" if row.status in {"OVER-HEDGED", "UNMATCHED"} else "MEDIUM"
                findings.append(AgentFinding(
                    agent=self.name,
                    severity=severity,
                    title=f"{row.currency} hedge coverage: {row.status.lower()}",
                    message="FX hedge coverage falls outside configured treasury policy or lacks a matching business exposure.",
                    metric=(f"{(row.hedge_ratio * 100):.1f}%" if row.hedge_ratio is not None else "No underlying exposure"),
                ))
        return findings
