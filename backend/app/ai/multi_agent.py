from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Literal

from app.integrations.astra import AstraRequest, AstraTreasuryReasoner
from app.schemas.treasury import AgentFinding


@dataclass(frozen=True)
class SpecialistProfile:
    name: str
    instruction: str


PROFILES = {
    "Liquidity Agent": SpecialistProfile(
        "Liquidity Agent",
        "Act as a group treasury liquidity specialist. Focus on available liquidity, entity deficits, trapped/committed cash, buffers and funding actions.",
    ),
    "Liquidity Forecast Agent": SpecialistProfile(
        "Liquidity Forecast Agent",
        "Act as a short-term cash forecasting specialist. Focus on timing, forecast uncertainty, buffer breaches and early-warning indicators.",
    ),
    "Funding Agent": SpecialistProfile(
        "Funding Agent",
        "Act as a corporate funding specialist. Focus on facility utilization, maturity/refinancing risk and committed funding capacity.",
    ),
    "FX Risk Agent": SpecialistProfile(
        "FX Risk Agent",
        "Act as an MNC FX risk specialist. Focus on residual business exposure and hedge-policy compliance. Never propose speculative positions.",
    ),
    "Derivatives & Hedge Agent": SpecialistProfile(
        "Derivatives & Hedge Agent",
        "Act as a corporate derivatives risk specialist. Focus on hedge linkage, maturity, MTM, settlement liquidity and hedge coverage.",
    ),
    "Interest Rate Risk Agent": SpecialistProfile(
        "Interest Rate Risk Agent",
        "Act as a corporate interest-rate risk specialist. Focus on floating debt, hedge offsets and cash-interest sensitivity.",
    ),
    "Counterparty Risk Agent": SpecialistProfile(
        "Counterparty Risk Agent",
        "Act as a derivatives counterparty-risk specialist. Focus on positive MTM, PFE, approved limits and concentration.",
    ),
    "Market Risk Agent": SpecialistProfile(
        "Market Risk Agent",
        "Act as a treasury market-risk specialist. Focus on FX/rate shocks and their potential liquidity implications, not trading predictions.",
    ),
    "Integrated Stress Agent": SpecialistProfile(
        "Integrated Stress Agent",
        "Act as a treasury stress-testing specialist. Challenge base assumptions and distinguish operating liquidity stress from market-risk overlays.",
    ),
    "Cash Mobility & Pooling Agent": SpecialistProfile(
        "Cash Mobility & Pooling Agent",
        "Act as a global cash-management specialist. Focus on trapped cash, cash pools, local minimums and legal-entity liquidity mobility. Never assume cash can cross borders without validated constraints.",
    ),
    "Cross-Border Funding & Tax Agent": SpecialistProfile(
        "Cross-Border Funding & Tax Agent",
        "Act as an intercompany funding and treasury-tax specialist. Compare validated funding facts, transfer-pricing ranges and configured tax rules. Treat non-final tax rules as review items, not legal advice.",
    ),
    "Collateral & CSA Agent": SpecialistProfile(
        "Collateral & CSA Agent",
        "Act as a collateral-liquidity specialist. Focus on CSA thresholds, MTA, posted collateral and stressed margin calls. Keep collateral liquidity separate from operating cash forecasts.",
    ),
    "Refinancing & Covenant Agent": SpecialistProfile(
        "Refinancing & Covenant Agent",
        "Act as a refinancing and covenant-risk specialist. Focus on debt maturities, facility expiries, covenant headroom and potential acceleration or liquidity consequences.",
    ),
    "Policy Agent": SpecialistProfile(
        "Policy Agent",
        "Act as an independent treasury-policy controller. Policy limits are hard constraints and cannot be overridden by AI recommendations.",
    ),
    "Model Risk Challenger": SpecialistProfile(
        "Model Risk Challenger",
        "Challenge data quality, unsupported conclusions, stale inputs, mapping gaps and model limitations. Prefer caution over false precision.",
    ),

    "Market Data Integrity Agent": SpecialistProfile(
        "Market Data Integrity Agent",
        "Act as a treasury market-data control specialist. Focus on source freshness, primary/backup availability and whether data is fit for risk measurement or execution.",
    ),
    "Treasury Reconciliation Agent": SpecialistProfile(
        "Treasury Reconciliation Agent",
        "Act as a treasury operations control specialist. Focus on bank-to-ledger and ERP-to-treasury reconciliation breaks, connector health and release blockers.",
    ),
    "Hedge Accounting Control Agent": SpecialistProfile(
        "Hedge Accounting Control Agent",
        "Act as a hedge-accounting control specialist. Distinguish economic hedge effectiveness from accounting designation, documentation and effectiveness testing.",
    ),
    "Treasury Execution Control Agent": SpecialistProfile(
        "Treasury Execution Control Agent",
        "Act as an independent treasury execution-control specialist. Focus on maker-checker, segregation of duties, pre-trade blocks, approvals and release-to-execution status.",
    ),
    "Payment Behaviour Agent": SpecialistProfile("Payment Behaviour Agent", "Act as a receivables and payment-behaviour specialist. Use only validated model outputs and focus on collection timing risk, uncertainty and liquidity implications."),
    "ML Cash Forecast Agent": SpecialistProfile("ML Cash Forecast Agent", "Act as a model-aware cash forecasting specialist. Explain confidence bands, validation status and conservative liquidity paths without overstating precision."),
    "Intraday Liquidity Agent": SpecialistProfile("Intraday Liquidity Agent", "Act as an intraday liquidity specialist. Focus on payment timing, buffers, committed facilities and funding peaks. Do not autonomously reorder contractual payments."),
    "Treasury Anomaly Detection Agent": SpecialistProfile("Treasury Anomaly Detection Agent", "Act as an independent payment anomaly investigator. Treat model flags as review signals, not proof of fraud or misconduct."),
    "Model Governance & Drift Agent": SpecialistProfile("Model Governance & Drift Agent", "Act as treasury model-risk governance. Focus on validation metrics, drift, data fitness, limitations and escalation thresholds."),
    "Independent Price Verification Agent": SpecialistProfile("Independent Price Verification Agent", "Act as an independent valuation control specialist. Compare book MTM with independent sources and escalate valuation differences; do not invent prices."),
    "Integrated Scenario Orchestration Agent": SpecialistProfile("Integrated Scenario Orchestration Agent", "Act as enterprise treasury stress orchestration. Keep operating liquidity, market value sensitivity, collateral and refinancing effects distinct and avoid double counting."),
    "Payment Screening Control Agent": SpecialistProfile("Payment Screening Control Agent", "Act as a payment-screening control specialist. Unresolved potential matches block execution pending human compliance review; never decide sanctions status yourself."),

    "Institutional Pricing & Valuation Agent": SpecialistProfile("Institutional Pricing & Valuation Agent", "Act as an independent derivatives valuation specialist. Use approved curves, volatility inputs and governed pricing models only. Distinguish model value from book MTM and never invent market inputs."),
    "Liquidity-at-Risk Agent": SpecialistProfile("Liquidity-at-Risk Agent", "Act as a quantitative liquidity-risk specialist. Explain LaR/CFaR distributions, tail funding needs and model limitations. Never present a percentile as a guaranteed maximum loss."),
    "Legal Netting & Counterparty Agent": SpecialistProfile("Legal Netting & Counterparty Agent", "Act as a counterparty credit and legal-netting specialist. Recognize close-out netting only when legal enforceability is approved; otherwise use gross exposure."),
    "Collateral Optimization Agent": SpecialistProfile("Collateral Optimization Agent", "Act as a collateral-liquidity specialist. Optimize funding source visibility while preserving legal-entity buffers, eligibility rules and human approval."),
    "Champion-Challenger Model Agent": SpecialistProfile("Champion-Challenger Model Agent", "Act as independent model-risk governance. Compare champion and challenger performance but never auto-promote a model; require independent validation and approval."),
    "Operational Resilience & Security Agent": SpecialistProfile("Operational Resilience & Security Agent", "Act as treasury technology resilience and security control specialist. Focus on identity, database, RTO/RPO, disaster recovery, critical dependencies and production-readiness gaps."),
    "Live Event Integrity Agent": SpecialistProfile(
        "Live Event Integrity Agent",
        "Act as a real-time treasury data-integrity specialist. Focus on event idempotency, sequencing, out-of-order quarantine, schema compatibility and arrival lag. Never treat a quarantined event as current state.",
    ),
    "Connector Stream Health Agent": SpecialistProfile(
        "Connector Stream Health Agent",
        "Act as a treasury integration reliability specialist. Focus on checkpoints, event watermarks, stale streams, duplicates and connector degradation without inventing missing data.",
    ),
    "Execution Messaging & Acknowledgement Agent": SpecialistProfile(
        "Execution Messaging & Acknowledgement Agent",
        "Act as a treasury execution-operations controller. Distinguish release, connector dispatch, bank acknowledgement and rejection. A queued or sent message is not proof of completed execution.",
    ),
    "Continuous Treasury Monitoring Agent": SpecialistProfile(
        "Continuous Treasury Monitoring Agent",
        "Act as a continuous treasury surveillance specialist. Prioritize liquidity survival and control breaches. Monitoring is advisory only and cannot create, approve, release or execute a transaction.",
    ),
    "Data Quality Agent": SpecialistProfile(
        "Data Quality Agent",
        "Act as treasury data-control specialist. Identify stale, missing or inconsistent inputs that invalidate risk conclusions.",
    ),
}


PROFILES.update({
    "Treasury Digital Twin Agent": SpecialistProfile("Treasury Digital Twin Agent", "Act as a treasury digital-twin specialist. Keep operating liquidity, market risk, collateral, refinancing and intraday risk distinct. Use the twin for scenario decision support only; it has no execution authority."),
    "Market VaR & EaR Agent": SpecialistProfile("Market VaR & EaR Agent", "Act as a corporate treasury market-risk distribution specialist. Explain residual FX VaR, expected shortfall and earnings-at-risk with model limitations. Never present VaR as a worst-case bound."),
    "Liquidity Transfer Pricing Agent": SpecialistProfile("Liquidity Transfer Pricing Agent", "Act as an internal liquidity economics specialist. Use governed benchmark curves and transparent liquidity spreads. Distinguish management liquidity pricing from legal or tax transfer pricing."),
    "Bank Account Rationalization Agent": SpecialistProfile("Bank Account Rationalization Agent", "Act as a global bank-account architecture specialist. Focus on stale accounts, low utilization, pooling roles, restrictions and concentration. Never recommend closure without operational/legal review."),
    "Enterprise Treasury Risk Committee Agent": SpecialistProfile("Enterprise Treasury Risk Committee Agent", "Act as a treasury risk committee challenger. Integrate validated liquidity, market, intraday, collateral and refinancing evidence without changing deterministic results or execution controls."),
})

PROFILES.update({
    "Portfolio Hedge Optimization Agent": SpecialistProfile("Portfolio Hedge Optimization Agent", "Act as a portfolio hedging optimization specialist. Use policy-constrained business exposures, explicit cost assumptions and validated hedge data. Never forecast market direction or create speculative trades."),
    "Funding Optimization Agent": SpecialistProfile("Funding Optimization Agent", "Act as a treasury funding optimization specialist. Prioritize liquidity survival, committed capacity, funding diversification and transparent cost-data gaps. Never double count intercompany facilities as new group cash."),
    "Cash Allocation Optimization Agent": SpecialistProfile("Cash Allocation Optimization Agent", "Act as a global cash allocation specialist. Optimize cash-pool offsets only within validated transferable balances, local buffers, tax/legal constraints and approved pool membership."),
    "Treasury Scenario Search Agent": SpecialistProfile("Treasury Scenario Search Agent", "Act as a treasury reverse-scenario and search specialist. Compare configured stress combinations, identify vulnerability clusters and never attach probabilities to deterministic grid-search outcomes."),
    "Cost of Liquidity Agent": SpecialistProfile("Cost of Liquidity Agent", "Act as a funding economics and liquidity-cost specialist. Highlight missing executable pricing rather than inventing spreads, all-in costs or ranking unsupported funding sources."),
    "Treasury Decision Committee Agent": SpecialistProfile("Treasury Decision Committee Agent", "Act as the synthesis member of a treasury decision committee. Compare validated strategies across liquidity, risk, cost, controls and resilience. You have no approval or execution authority."),
})

PROFILES.update({
    "Historical Market Calibration Agent": SpecialistProfile("Historical Market Calibration Agent", "Act as an institutional market-risk calibration specialist. Focus on approved history, EWMA volatility, dynamic correlations, lineage and calibration limitations."),
    "Counterparty XVA Sensitivity Agent": SpecialistProfile("Counterparty XVA Sensitivity Agent", "Act as a counterparty valuation-adjustment risk specialist. Treat CVA/FVA outputs as governed risk sensitivities unless accounting valuation governance explicitly approves them."),
    "Liquidity Survival Horizon Agent": SpecialistProfile("Liquidity Survival Horizon Agent", "Act as a liquidity-survival specialist. Focus on days-to-breach, funding exhaustion and contingency triggers without assuming contingent facilities are guaranteed cash."),
    "Funding Concentration Agent": SpecialistProfile("Funding Concentration Agent", "Act as a funding concentration specialist. Focus on lender dependence, maturity clustering and diversification risk."),
    "Treasury Risk Limit Framework Agent": SpecialistProfile("Treasury Risk Limit Framework Agent", "Act as independent treasury risk-limit governance. Treat limits and warnings as hard governance inputs that AI cannot override."),
    "Digital Twin Scenario Optimizer Agent": SpecialistProfile("Digital Twin Scenario Optimizer Agent", "Act as a treasury resilience scenario optimizer. Compare governed configurations without assigning unsupported probabilities or execution authority."),
    "Structural Liquidity Gap Agent": SpecialistProfile("Structural Liquidity Gap Agent", "Act as a structural liquidity-gap specialist. Keep contractual cash flows, contingent facilities and minimum buffers distinct across maturity buckets."),
    "Interest Rate Gap & DV01 Agent": SpecialistProfile("Interest Rate Gap & DV01 Agent", "Act as an interest-rate gap and DV01 specialist. Distinguish cash-interest sensitivity, economic-value sensitivity and proxy limitations."),
    "Funding Tenor Optimization Agent": SpecialistProfile("Funding Tenor Optimization Agent", "Act as a funding-tenor resilience specialist. Balance maturity concentration, refinancing risk and liquidity survival without inventing executable funding prices."),
    "Cross-Currency Funding Structuring Agent": SpecialistProfile("Cross-Currency Funding Structuring Agent", "Act as a cross-currency corporate funding specialist. Compare structures only with validated FX, hedge, tax, legal and regulatory inputs."),
    "Contingency Funding Plan Agent": SpecialistProfile("Contingency Funding Plan Agent", "Act as a contingency funding specialist. Preserve sequential liquidity-source use and prevent double counting across cash, facilities and new funding."),
    "Treasury Early Warning Agent": SpecialistProfile("Treasury Early Warning Agent", "Act as an early-warning governance specialist. Interpret directional thresholds and escalation status without changing approved thresholds."),
    "Predictive Balance-Sheet Twin Agent": SpecialistProfile("Predictive Balance-Sheet Twin Agent", "Act as a balance-sheet treasury simulation specialist. Keep liquidity, rate, FX, collateral and refinancing impacts separately attributable."),
    "Liquidity Concentration Agent": SpecialistProfile("Liquidity Concentration Agent", "Act as a liquidity concentration and cash-transferability specialist. Distinguish headline cash concentration from legally transferable liquidity."),
    "Probabilistic Liquidity Path Agent": SpecialistProfile("Probabilistic Liquidity Path Agent", "Act as a probabilistic liquidity-path specialist. Explain breach probability, tail funding needs and path uncertainty without treating percentiles as guarantees."),
    "Liquidity Stress Attribution Agent": SpecialistProfile("Liquidity Stress Attribution Agent", "Act as a liquidity stress-attribution specialist. Identify standalone drivers and interaction residuals while preserving economic-value versus cash-flow transmission boundaries."),
    "Forecast Driver Concentration Agent": SpecialistProfile("Forecast Driver Concentration Agent", "Act as a cash-forecast driver specialist. Focus on counterparty and flow concentration, probability weighting and forecast dependency risk."),
    "Liquidity Action Playbook Agent": SpecialistProfile("Liquidity Action Playbook Agent", "Act as a contingency action-playbook specialist. Prioritize governed, non-executable actions and never double count liquidity capacity."),
    "Audit & Traceability Agent": SpecialistProfile("Audit & Traceability Agent", "Act as an independent treasury audit-trace specialist. Focus on evidence, data lineage, approvals and reproducibility; do not alter business decisions."),
})



TOP_LEVEL_AGENT_TEAMS = {
    "Liquidity & Funding Agent": "Own liquidity, cash forecasting, working capital, funding, refinancing, survival horizon and contingency funding. Preserve legal-entity buffers and avoid liquidity double counting.",
    "Market & Derivatives Risk Agent": "Own FX, rates, derivatives, hedge effectiveness, valuation, collateral, counterparty and market-risk analytics. Never create speculative trading recommendations.",
    "Global Treasury & Tax Agent": "Own cash mobility, pooling, intercompany funding, cross-border constraints, tax-aware treasury structures and legal-entity transferability. Never treat unreviewed tax/legal rules as executable.",
    "Risk, Controls & Model Governance Agent": "Own policy, limits, model risk, data quality, reconciliations, execution controls, security, resilience, auditability and screening. Controls cannot be overridden by AI.",
    "Treasury Orchestrator & Decision Agent": "Synthesize validated outputs, scenarios and strategy alternatives for treasury management. Separate facts, assumptions and recommendations and retain zero approval/execution authority.",
}


def team_for_specialist(name: str) -> str:
    n = name.lower()
    if any(x in n for x in ["cash mobility", "cross-border", "tax", "legal netting", "bank rationalization", "liquidity transfer pricing", "cross-currency funding"]):
        return "Global Treasury & Tax Agent"
    if any(x in n for x in ["fx ", "fx risk", "derivative", "interest rate", "market risk", "counterparty", "collateral", "hedge", "pricing", "xva", "var", "ear", "ipv"]):
        return "Market & Derivatives Risk Agent"
    if any(x in n for x in ["liquidity", "forecast", "funding", "refinancing", "survival", "working capital", "receivables", "intraday", "contingency"]):
        return "Liquidity & Funding Agent"
    if any(x in n for x in ["policy", "model", "data quality", "reconciliation", "execution", "screening", "security", "resilience", "live event", "stream health", "audit", "champion"]):
        return "Risk, Controls & Model Governance Agent"
    return "Treasury Orchestrator & Decision Agent"


class AstraMultiAgentRuntime:
    """Token-aware multi-agent LLM layer.

    SELECTIVE: call only specialists with HIGH/MEDIUM/CRITICAL findings.
    FULL: call all specialist profiles represented in findings.
    DETERMINISTIC: no LLM calls.
    """

    def __init__(self) -> None:
        self.reasoner = AstraTreasuryReasoner()

    def select_agents(
        self,
        findings: list[AgentFinding],
        mode: Literal["DETERMINISTIC", "SELECTIVE", "FULL"] = "SELECTIVE",
    ) -> list[str]:
        represented = [name for name in PROFILES if any(f.agent == name for f in findings)]
        if mode == "DETERMINISTIC":
            return []
        if mode == "FULL":
            return represented
        material = {f.agent for f in findings if f.severity in {"CRITICAL", "HIGH", "MEDIUM"}}
        return [name for name in represented if name in material]

    async def analyze(
        self,
        question: str,
        findings: list[AgentFinding],
        shared_context: dict,
        mode: Literal["DETERMINISTIC", "SELECTIVE", "FULL"] = "SELECTIVE",
    ) -> list[dict]:
        selected = self.select_agents(findings, mode)
        if not selected:
            return []

        # Specialist findings are preserved, but GPT-6 Astra reasoning is consolidated into
        # five senior agent teams to reduce latency/tokens without reducing deterministic coverage.
        grouped: dict[str, list[str]] = {}
        for name in selected:
            grouped.setdefault(team_for_specialist(name), []).append(name)

        async def run_team(team_name: str, members: list[str]) -> tuple[str, list[str], object]:
            local_findings = [f.model_dump() for f in findings if f.agent in members]
            response = await self.reasoner.explain(AstraRequest(
                task=question,
                system_instruction=(
                    TOP_LEVEL_AGENT_TEAMS[team_name]
                    + " Use only validated engine outputs from your specialist capabilities. Do not invent numbers. "
                    + "Material treasury actions require human approval and deterministic controls remain authoritative."
                ),
                validated_context={
                    "shared": shared_context,
                    "team": team_name,
                    "specialist_capabilities": members,
                    "specialist_findings": local_findings,
                },
                max_output_tokens=420,
            ))
            return team_name, members, response

        team_results = await asyncio.gather(*(run_team(team, members) for team, members in grouped.items()))
        expanded: list[dict] = []
        for team_name, members, response in team_results:
            for name in members:
                expanded.append({
                    "agent": name,
                    "model": response.model,
                    "enabled": response.enabled,
                    "text": None if response.text is None else f"[{team_name}] {response.text}",
                    "response_id": response.response_id,
                    "error": response.error,
                })
        return expanded

PROFILES.update({
    "Forecast Accuracy & Bias Agent": SpecialistProfile(
        "Forecast Accuracy & Bias Agent",
        "Act as an independent treasury cash-forecast performance specialist. Interpret WAPE, horizon accuracy and liquidity-direction bias. Never hide systematic optimistic bias and never modify realized history.",
    ),
    "Working Capital Cycle Agent": SpecialistProfile(
        "Working Capital Cycle Agent",
        "Act as a working-capital treasury specialist. Analyze DSO, DPO, DIO and cash conversion cycle while separating liquidity management from accounting judgments and commercial ownership.",
    ),
    "Receivables Collection Risk Agent": SpecialistProfile(
        "Receivables Collection Risk Agent",
        "Act as a receivables-liquidity risk specialist. Focus on aging, collection probability, overdue concentration and treasury cash timing. Do not treat collection probability as an impairment or credit-loss accounting estimate.",
    ),
    "Working Capital Liquidity Agent": SpecialistProfile(
        "Working Capital Liquidity Agent",
        "Act as a working-capital liquidity scenario specialist. Quantify potential cash release from DSO, DPO and inventory changes as advisory scenarios only, with no authority to alter customer, supplier or inventory terms.",
    ),
})
