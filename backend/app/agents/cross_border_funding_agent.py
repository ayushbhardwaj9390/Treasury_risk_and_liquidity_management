from sqlalchemy.orm import Session
from app.agents.base import TreasuryAgent
from app.schemas.treasury import AgentFinding
from app.services.global_treasury import calculate_cross_border_funding


class CrossBorderFundingAgent(TreasuryAgent):
    name = "Cross-Border Funding & Tax Agent"

    def run(self, db: Session) -> list[AgentFinding]:
        findings: list[AgentFinding] = []
        for option in calculate_cross_border_funding(db):
            if option.transfer_pricing_status == "OUTSIDE_CONFIGURED_RANGE":
                findings.append(AgentFinding(
                    agent=self.name,
                    severity="HIGH",
                    title="Intercompany pricing outside configured range",
                    message=f"{option.lender_entity} → {option.borrower_entity} facility rate is outside the configured transfer-pricing range; tax review is required before use.",
                ))
            if option.tax_rule_status in {"TAX_RULE_MISSING", "REVIEW_REQUIRED"}:
                findings.append(AgentFinding(
                    agent=self.name,
                    severity="MEDIUM",
                    title="Cross-border tax review required",
                    message=f"{option.lender_entity} → {option.borrower_entity} funding has a non-final tax rule status ({option.tax_rule_status}); do not treat estimated tax cost as approved advice.",
                ))
        return findings
