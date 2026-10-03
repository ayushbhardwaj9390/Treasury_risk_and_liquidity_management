from sqlalchemy.orm import Session
from app.agents.base import TreasuryAgent
from app.schemas.treasury import AgentFinding
from app.services.global_treasury import calculate_cash_mobility, calculate_cash_pools


class CashMobilityAgent(TreasuryAgent):
    name = "Cash Mobility & Pooling Agent"

    def run(self, db: Session) -> list[AgentFinding]:
        mobility = calculate_cash_mobility(db)
        pools = calculate_cash_pools(db)
        findings: list[AgentFinding] = []
        if mobility.total_trapped_cash > 0:
            findings.append(AgentFinding(
                agent=self.name,
                severity="MEDIUM",
                title="Trapped cash identified",
                message=f"{mobility.reporting_currency} {mobility.total_trapped_cash:,.0f} of cash above operating minimums is subject to configured mobility restrictions.",
                metric=str(mobility.total_trapped_cash),
            ))
        if mobility.total_local_cash_deficit > 0 and mobility.total_transferable_surplus > mobility.total_local_cash_deficit:
            findings.append(AgentFinding(
                agent=self.name,
                severity="MEDIUM",
                title="Internal liquidity offset opportunity",
                message="Local cash deficits coexist with transferable group surplus. Evaluate pooling or intercompany funding before incremental external borrowing, subject to tax/regulatory approval.",
            ))
        for pool in pools:
            if pool.internal_offset_capacity > 0:
                findings.append(AgentFinding(
                    agent=self.name,
                    severity="INFO",
                    title=f"{pool.pool_name} can offset local needs",
                    message=f"Internal offset capacity is {pool.currency} {pool.internal_offset_capacity:,.0f} based on current pool balances and sweep targets.",
                ))
        return findings
