from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.agents.audit_agent import AuditAgent
from app.agents.cash_mobility_agent import CashMobilityAgent
from app.agents.cross_border_funding_agent import CrossBorderFundingAgent
from app.agents.collateral_agent import CollateralAgent
from app.agents.refinancing_agent import RefinancingAgent
from app.agents.counterparty_agent import CounterpartyAgent
from app.agents.data_quality_agent import DataQualityAgent
from app.agents.derivatives_agent import DerivativesAgent
from app.agents.forecast_agent import ForecastAgent
from app.agents.funding_agent import FundingAgent
from app.agents.fx_risk_agent import FXRiskAgent
from app.agents.interest_rate_agent import InterestRateAgent
from app.agents.liquidity_agent import LiquidityAgent
from app.agents.market_risk_agent import MarketRiskAgent
from app.agents.model_risk_agent import ModelRiskAgent
from app.agents.policy_agent import PolicyAgent
from app.agents.stress_agent import StressAgent
from app.agents.market_data_agent import MarketDataIntegrityAgent
from app.agents.reconciliation_agent import ReconciliationAgent
from app.agents.hedge_accounting_agent import HedgeAccountingAgent
from app.agents.execution_control_agent import ExecutionControlAgent
from app.agents.payment_behavior_agent import PaymentBehaviorAgent
from app.agents.ml_forecast_agent import MLForecastAgent
from app.agents.intraday_liquidity_agent import IntradayLiquidityAgent
from app.agents.anomaly_agent import PaymentAnomalyAgent
from app.agents.model_governance_agent import ModelGovernanceAgent
from app.agents.ipv_agent import IndependentPriceVerificationAgent
from app.agents.scenario_orchestration_agent import ScenarioOrchestrationAgent
from app.agents.payment_screening_agent import PaymentScreeningAgent
from app.agents.institutional_pricing_agent import InstitutionalPricingAgent
from app.agents.liquidity_at_risk_agent import LiquidityAtRiskAgent
from app.agents.legal_netting_agent import LegalNettingAgent
from app.agents.collateral_optimization_agent import CollateralOptimizationAgent
from app.agents.champion_challenger_agent import ChampionChallengerAgent
from app.agents.resilience_security_agent import ResilienceSecurityAgent
from app.agents.live_event_agent import LiveEventIntegrityAgent
from app.agents.stream_health_agent import StreamHealthAgent
from app.agents.execution_messaging_agent import ExecutionMessagingAgent
from app.agents.continuous_monitor_agent import ContinuousMonitorAgent
from app.agents.hedge_optimization_agent import HedgeOptimizationAgent
from app.agents.funding_optimization_agent import FundingOptimizationAgent
from app.agents.cash_allocation_agent import CashAllocationOptimizationAgent
from app.agents.scenario_search_agent import ScenarioSearchAgent
from app.agents.cost_of_liquidity_agent import CostOfLiquidityAgent
from app.agents.decision_committee_agent import TreasuryDecisionCommitteeAgent
from app.agents.digital_twin_agent import TreasuryDigitalTwinAgent
from app.agents.market_var_agent import MarketVaREaRAgent
from app.agents.liquidity_transfer_pricing_agent import LiquidityTransferPricingAgent
from app.agents.bank_rationalization_agent import BankRationalizationAgent
from app.agents.enterprise_risk_committee_agent import EnterpriseRiskCommitteeAgent
from app.agents.historical_market_agent import HistoricalMarketCalibrationAgent
from app.agents.xva_agent import XVAAgent
from app.agents.survival_horizon_agent import LiquiditySurvivalHorizonAgent
from app.agents.funding_concentration_agent import FundingConcentrationAgent
from app.agents.risk_limit_agent import TreasuryRiskLimitAgent
from app.agents.digital_twin_optimizer_agent import DigitalTwinScenarioOptimizerAgent
from app.agents.structural_liquidity_agent import StructuralLiquidityAgent
from app.agents.rate_gap_dv01_agent import RateGapDV01Agent
from app.agents.funding_tenor_agent import FundingTenorAgent
from app.agents.cross_currency_funding_optimization_agent import CrossCurrencyFundingOptimizationAgent
from app.agents.contingency_funding_agent import ContingencyFundingPlanAgent
from app.agents.early_warning_agent import TreasuryEarlyWarningAgent
from app.agents.balance_sheet_twin_agent import BalanceSheetTwinAgent
from app.agents.liquidity_concentration_agent import LiquidityConcentrationAgent
from app.agents.probabilistic_liquidity_agent import ProbabilisticLiquidityAgent
from app.agents.liquidity_attribution_agent import LiquidityStressAttributionAgent
from app.agents.forecast_driver_agent import ForecastDriverConcentrationAgent
from app.agents.liquidity_playbook_agent import LiquidityActionPlaybookAgent
from app.agents.forecast_accuracy_agent import ForecastAccuracyAgent
from app.agents.working_capital_agent import WorkingCapitalCycleAgent
from app.agents.receivables_collection_agent import ReceivablesCollectionRiskAgent
from app.agents.working_capital_liquidity_agent import WorkingCapitalLiquidityAgent
from app.core.config import settings
from app.ai.multi_agent import AstraMultiAgentRuntime, TOP_LEVEL_AGENT_TEAMS
from app.integrations.astra import AstraRequest, AstraTreasuryReasoner
from app.models import AuditLog
from app.schemas.treasury import AgentRuntimeStatus, MultiAgentAnalysisResponse, SpecialistAIInsight, TreasuryCopilotResponse, TreasurySummary
from app.services.derivative_risk import derivative_risk_summary
from app.services.forecast import calculate_liquidity_forecast
from app.services.liquidity import calculate_global_liquidity
from app.services.market_stress import calculate_market_stress
from app.services.global_treasury import calculate_cash_mobility, calculate_collateral_liquidity, calculate_refinancing_risk
from app.services.enterprise_controls import market_data_health, latest_reconciliations, hedge_accounting_status, list_transaction_proposals
from app.services.scenario_risk import reverse_stress_collections
from app.services.advanced_intelligence import payment_model_drift, independent_price_verification, calculate_intraday_liquidity, payment_screening_status
from app.services.live_operations import live_operations_status, list_execution_messages
from app.services.treasury_optimization import optimize_fx_hedges, optimize_funding
from app.services.digital_twin import run_digital_twin, calculate_market_risk_distribution, calculate_liquidity_transfer_pricing, calculate_bank_account_rationalization
from app.services.mvp11_risk import calculate_historical_market_risk, calculate_xva_style_adjustments, calculate_liquidity_survival_horizon, calculate_funding_concentration, evaluate_treasury_risk_limits
from app.services.mvp12_liquidity_command import (
    calculate_structural_liquidity_gap,
    calculate_interest_rate_gap_dv01,
    optimize_funding_tenor,
    analyze_cross_currency_funding,
    build_contingency_funding_plan,
    calculate_early_warning_indicators,
    run_balance_sheet_twin,
)
from app.services.mvp15_20_enterprise import (
    cross_border_constraint_graph,
    optimize_legal_entity_liquidity,
    enterprise_connector_readiness,
    enterprise_security_posture,
    model_validation_dashboard,
    production_readiness,
)
from app.services.mvp21_22_predictive_strategy import (
    calculate_treasury_risk_radar,
    calculate_optimal_liquidity_buffer,
    optimize_strategic_treasury,
)
from app.services.mvp14_forecast_working_capital import (
    calculate_forecast_accuracy,
    calculate_forecast_bias,
    calculate_working_capital_cycle,
    calculate_receivables_aging,
)


class TreasuryOrchestrator:
    """Coordinates deterministic specialist agents and optional GPT-6 Astra synthesis."""

    def __init__(self):
        self.agents = [
            DataQualityAgent(),
            LiquidityAgent(),
            ForecastAgent(),
            FundingAgent(),
            FXRiskAgent(),
            DerivativesAgent(),
            InterestRateAgent(),
            CounterpartyAgent(),
            MarketRiskAgent(),
            StressAgent(),
            CashMobilityAgent(),
            CrossBorderFundingAgent(),
            CollateralAgent(),
            RefinancingAgent(),
            PolicyAgent(),
            ModelRiskAgent(),
            MarketDataIntegrityAgent(),
            ReconciliationAgent(),
            HedgeAccountingAgent(),
            ExecutionControlAgent(),
            PaymentBehaviorAgent(),
            MLForecastAgent(),
            IntradayLiquidityAgent(),
            PaymentAnomalyAgent(),
            ModelGovernanceAgent(),
            IndependentPriceVerificationAgent(),
            ScenarioOrchestrationAgent(),
            PaymentScreeningAgent(),
            InstitutionalPricingAgent(),
            LiquidityAtRiskAgent(),
            LegalNettingAgent(),
            CollateralOptimizationAgent(),
            ChampionChallengerAgent(),
            ResilienceSecurityAgent(),
            LiveEventIntegrityAgent(),
            StreamHealthAgent(),
            ExecutionMessagingAgent(),
            ContinuousMonitorAgent(),
            HedgeOptimizationAgent(),
            FundingOptimizationAgent(),
            CashAllocationOptimizationAgent(),
            ScenarioSearchAgent(),
            CostOfLiquidityAgent(),
            TreasuryDecisionCommitteeAgent(),
            TreasuryDigitalTwinAgent(),
            MarketVaREaRAgent(),
            LiquidityTransferPricingAgent(),
            BankRationalizationAgent(),
            EnterpriseRiskCommitteeAgent(),
            HistoricalMarketCalibrationAgent(),
            XVAAgent(),
            LiquiditySurvivalHorizonAgent(),
            FundingConcentrationAgent(),
            TreasuryRiskLimitAgent(),
            DigitalTwinScenarioOptimizerAgent(),
            StructuralLiquidityAgent(),
            RateGapDV01Agent(),
            FundingTenorAgent(),
            CrossCurrencyFundingOptimizationAgent(),
            ContingencyFundingPlanAgent(),
            TreasuryEarlyWarningAgent(),
            BalanceSheetTwinAgent(),
            LiquidityConcentrationAgent(),
            ForecastDriverConcentrationAgent(),
            AuditAgent(),
        ]
        # Heavy analytics remain deployed but are invoked on demand rather than on every summary request.
        self.on_demand_agents = [
            ProbabilisticLiquidityAgent(),
            LiquidityStressAttributionAgent(),
            LiquidityActionPlaybookAgent(),
            ForecastAccuracyAgent(),
            WorkingCapitalCycleAgent(),
            ReceivablesCollectionRiskAgent(),
            WorkingCapitalLiquidityAgent(),
        ]
        self.reasoner = AstraTreasuryReasoner()
        self.multi_agent = AstraMultiAgentRuntime()

    @staticmethod
    def _status(findings) -> str:
        severities = {f.severity for f in findings}
        if "CRITICAL" in severities:
            return "CRITICAL"
        if "HIGH" in severities:
            return "HIGH RISK"
        if "MEDIUM" in severities:
            return "WATCH"
        return "NORMAL"

    def run(self, db: Session, write_audit: bool = False) -> TreasurySummary:
        findings = []
        for agent in self.agents:
            findings.extend(agent.run(db))
        severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "INFO": 3}
        findings.sort(key=lambda item: (severity_order.get(item.severity, 9), item.agent, item.title))
        summary = TreasurySummary(
            ai_model=settings.ai_model_label,
            overall_status=self._status(findings),
            findings=findings,
        )
        if write_audit:
            db.add(AuditLog(
                event_type="MULTI_AGENT_TREASURY_RUN",
                actor="TREASURY_ORCHESTRATOR",
                details=(
                    f"agents={len(self.agents)}; findings={len(findings)}; "
                    f"status={summary.overall_status}; at={datetime.now(UTC).isoformat()}"
                ),
            ))
            db.commit()
        return summary

    def runtime_status(self) -> AgentRuntimeStatus:
        return AgentRuntimeStatus(
            model=settings.ai_model,
            llm_enabled=self.reasoner.enabled,
            top_level_agents=list(TOP_LEVEL_AGENT_TEAMS.keys()),
            specialist_agents=[agent.name for agent in [*self.agents, *self.on_demand_agents]],
            deterministic_engines=[
                "Global Liquidity Engine",
                "13-Week Forecast Engine",
                "FX Exposure Engine",
                "Derivative Risk Engine",
                "Interest Rate Risk Engine",
                "Counterparty PFE Engine",
                "Market Stress Engine",
                "Cash Mobility & Pooling Engine",
                "Cross-Border Funding & Tax Rules Engine",
                "Collateral / CSA Liquidity Engine",
                "Refinancing & Covenant Engine",
                "Pre-Trade Control Engine",
                "RBAC / Maker-Checker Engine",
                "Market Data Freshness Engine",
                "Reconciliation Control Engine",
                "Reverse Stress Search Engine",
                "Payment Behaviour ML Engine",
                "ML Cash Forecast Confidence Engine",
                "Intraday Liquidity Engine",
                "Payment Anomaly Isolation-Forest Engine",
                "Independent Price Verification Engine",
                "Integrated Treasury Scenario Engine",
                "Curve-Based Derivative Pricing Engine",
                "Liquidity-at-Risk / Cash-Flow-at-Risk Monte Carlo Engine",
                "Legal Netting Set Engine",
                "Collateral Optimization Engine",
                "Champion-Challenger Model Governance Engine",
                "Operational Resilience Engine",
                "Immutable Treasury Event Ledger & Projection Engine",
                "Connector Checkpoint / Watermark Engine",
                "Live Treasury Monitoring Engine",
                "Idempotent Execution Messaging & Acknowledgement Engine",
                "Portfolio Hedge Optimization Engine",
                "Contingency Funding Allocation Engine",
                "Cash-Pool Sweep Optimization Engine",
                "Multi-Factor Treasury Scenario Search Engine",
                "Treasury Strategy Decision Pack Engine",
                "Treasury Digital Twin Engine",
                "Residual FX VaR / Expected Shortfall / Earnings-at-Risk Engine",
                "Liquidity Transfer Pricing Engine",
                "Bank Account Rationalization Engine",
                "Historical EWMA Volatility & Dynamic Correlation Engine",
                "Counterparty CVA/FVA-Style Sensitivity Engine",
                "Liquidity Survival Horizon Engine",
                "Funding Concentration & HHI Engine",
                "Treasury Risk Limit Framework Engine",
                "Digital Twin Scenario Optimization Engine",
                "Structural Liquidity Maturity Ladder Engine",
                "Interest Rate Gap & DV01 Proxy Engine",
                "Funding Tenor Resilience Optimization Engine",
                "Cross-Currency Funding Structuring Engine",
                "Contingency Funding Plan Engine",
                "Treasury Early-Warning Indicator Engine",
                "Predictive Balance-Sheet Treasury Twin Engine",
                "Liquidity Concentration & Transferability Engine",
                "Probabilistic Weekly Liquidity Path Engine",
                "Liquidity Stress Attribution Engine",
                "Forecast Driver Concentration Engine",
                "Liquidity Action Playbook Engine",
                "Forecast Accuracy & Bias Engine",
                "Working Capital Cycle Engine",
                "Receivables Aging & Collection Risk Engine",
                "Working Capital Liquidity Bridge Engine",
                "Cross-Border Constraint Graph Engine",
                "Legal-Entity Liquidity Routing Optimizer",
                "Enterprise Connector Readiness Engine",
                "Enterprise Security Posture Engine",
                "Independent Model Validation Gate",
                "Role-Specific Investigation Workflow Engine",
                "Production Readiness Gate",
                "Predictive Treasury Risk Radar Engine",
                "Dynamic Market Regime Detection Engine",
                "Strategic Liquidity Buffer Optimization Engine",
                "Multi-Year Treasury Strategy Optimization Engine",
            ],
            controls=[
                "Treasury Policy Agent",
                "Model Risk Challenger",
                "Data Quality Agent",
                "Audit Trail",
                "Human approval boundary",
                "Segregation of duties",
                "Execution release boundary",
                "Model validation and drift monitoring",
                "Independent price verification",
                "Payment screening execution block",
                "Legal enforceability before netting recognition",
                "No automatic model promotion",
                "OIDC/JWT production identity boundary",
                "RTO/RPO and disaster-recovery controls",
                "Event idempotency and out-of-order quarantine",
                "Signed execution-message integrity boundary",
                "External bank acknowledgement required for completion",
                "Optimization outputs are advisory proposals only",
                "No AI or optimizer execution authority",
                "Digital twin has no transaction or execution authority",
                "Liquidity transfer pricing is management pricing, not tax advice",
                "CVA/FVA-style outputs are risk sensitivities until independently validated for accounting use",
                "Risk-limit breaches require human exception governance",
                "Historical calibration requires approved market-history lineage",
                "Balance-sheet twin outputs are simulations, not accounting forecasts",
                "Cross-currency funding recommendations require executable pricing and tax/regulatory review",
                "Contingency funding capacities are sequential to reduce liquidity double counting",
                "Probabilistic liquidity paths are decision-support distributions, not guaranteed funding outcomes",
                "Liquidity stress attribution preserves economic-value vs cash-flow transmission boundaries",
                "Liquidity playbook actions remain advisory and non-executable",
                "GPT-6 Astra reasoning is consolidated into five top-level agent teams",
                "Cross-border routing requires approved legal, regulatory and tax constraints",
                "Production deployment requires an explicit human release-board GO decision",
            ],
        )


    @staticmethod
    def _control_context(db: Session) -> dict:
        feeds = market_data_health(db)
        recons = latest_reconciliations(db)
        hedges = hedge_accounting_status(db)
        proposals = list_transaction_proposals(db)
        reverse = reverse_stress_collections(db)
        forecast_accuracy = calculate_forecast_accuracy(db)
        working_capital = calculate_working_capital_cycle(db)
        receivables_aging = calculate_receivables_aging(db)
        return {
            "primary_market_feeds_unusable": sum(1 for x in feeds if x.source_type == "PRIMARY" and not x.execution_usable),
            "reconciliation_failures": sum(1 for x in recons if x.status == "FAIL"),
            "reconciliation_warnings": sum(1 for x in recons if x.status == "WARN"),
            "pending_transaction_approvals": sum(1 for x in proposals if x.status in {"PENDING_APPROVAL", "PARTIALLY_APPROVED"}),
            "blocked_transaction_proposals": sum(1 for x in proposals if x.control_status == "BLOCKED"),
            "hedge_accounting_control_gaps": sum(1 for x in hedges if x.control_status != "READY"),
            "reverse_stress_collection_haircut_pct": str(reverse.collection_haircut_pct),
            "payment_model_drift": payment_model_drift(db).status,
            "ipv_failures": independent_price_verification(db).fail_count,
            "intraday_peak_funding_need": str(calculate_intraday_liquidity(db).peak_intraday_funding_need),
            "screening_blocks": sum(1 for x in payment_screening_status(db) if x.execution_blocked),
            "live_operations_status": live_operations_status(db).status,
            "live_event_failures_24h": live_operations_status(db).failed_24h,
            "live_event_quarantines_24h": live_operations_status(db).quarantined_24h,
            "execution_messages_pending_ack": sum(1 for x in list_execution_messages(db) if x.status in {"QUEUED", "SENT"}),
            "digital_twin_state": run_digital_twin(db).state,
            "market_var_95": str(calculate_market_risk_distribution(db, simulations=2000).portfolio_var_95),
            "bank_accounts_for_review": calculate_bank_account_rationalization(db).review_candidate_count,
            "historical_market_var_95": str(calculate_historical_market_risk(db).portfolio_var),
            "xva_style_total": str(calculate_xva_style_adjustments(db).total_xva_style_adjustment),
            "survival_horizon_days": calculate_liquidity_survival_horizon(db).survival_horizon_days,
            "top_lender_share": str(calculate_funding_concentration(db).top_lender_share),
            "risk_limit_status": evaluate_treasury_risk_limits(db).overall_status,
            "early_warning_status": calculate_early_warning_indicators(db).overall_status,
            "structural_cash_floor": str(calculate_structural_liquidity_gap(db).minimum_cumulative_cash_before_facilities),
            "rate_cash_impact_100bps": str(calculate_interest_rate_gap_dv01(db).annual_cash_impact_100bps),
            "contingency_funding_status": build_contingency_funding_plan(db).status,
            "forecast_accuracy_status": forecast_accuracy.status,
            "forecast_cash_bias_pct": str(forecast_accuracy.cash_bias_pct),
            "working_capital_ccc_days": str(working_capital.group_ccc_days),
            "overdue_receivables_share": str(receivables_aging.overdue_share),
            "cross_border_blocked_routes": cross_border_constraint_graph(db).blocked_route_count,
            "legal_entity_unresolved_deficit": str(optimize_legal_entity_liquidity(db).unresolved_deficit),
            "connector_blocked_count": enterprise_connector_readiness(db).blocked_count,
            "security_posture": enterprise_security_posture(db).overall_status,
            "model_validation_failures": model_validation_dashboard(db).fail_count,
            "production_readiness": production_readiness(db).overall_status,
            "treasury_risk_radar": calculate_treasury_risk_radar(db).overall_status,
            "risk_deterioration_score": str(calculate_treasury_risk_radar(db).deterioration_score),
            "strategic_liquidity_buffer": str(calculate_optimal_liquidity_buffer(db).recommended_buffer),
        }


    async def multi_agent_analysis(self, db: Session, question: str, mode: str = "SELECTIVE") -> MultiAgentAnalysisResponse:
        normalized = mode.upper()
        if normalized not in {"DETERMINISTIC", "SELECTIVE", "FULL"}:
            normalized = "SELECTIVE"
        summary = self.run(db, write_audit=True)
        question_lc = question.lower()
        if any(token in question_lc for token in ("liquidity", "cash", "funding", "buffer", "survival", "forecast", "working capital", "receivable", "payable", "dso", "dpo", "inventory", "ccc")):
            deep_findings = []
            for agent in self.on_demand_agents:
                deep_findings.extend(agent.run(db))
            merged = [*summary.findings, *deep_findings]
            severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "INFO": 3}
            merged.sort(key=lambda item: (severity_order.get(item.severity, 9), item.agent, item.title))
            summary = TreasurySummary(ai_model=summary.ai_model, overall_status=self._status(merged), findings=merged)
        liquidity = calculate_global_liquidity(db)
        severe = calculate_liquidity_forecast(db, "SEVERE")
        market = calculate_market_stress(db)
        shared = {
            "reporting_currency": liquidity.reporting_currency,
            "liquidity_headroom": str(liquidity.liquidity_headroom),
            "severe_breach_week": severe.first_buffer_breach_week,
            "severe_maximum_shortfall": str(severe.maximum_shortfall),
            "market_liquidity_overlay": str(market.combined_market_liquidity_call),
            "trapped_cash": str(calculate_cash_mobility(db).total_trapped_cash),
            "stressed_collateral_call": str(calculate_collateral_liquidity(db).stressed_margin_call),
            "debt_due_180d": str(calculate_refinancing_risk(db).debt_due_180d),
            "overall_status": summary.overall_status,
            "execution_controls": self._control_context(db),
            "optimization": {
                "incremental_hedge_reporting": str(optimize_fx_hedges(db).total_incremental_hedge_reporting),
                "tail_funding_need": str(optimize_funding(db).requested_funding_need),
                "tail_funding_uncovered": str(optimize_funding(db).uncovered_funding),
                "execution_authority": "NONE",
            },
            "digital_twin": {
                "state": run_digital_twin(db).state,
                "stressed_headroom": str(run_digital_twin(db).scenario_stressed_headroom),
                "market_var_95": str(calculate_market_risk_distribution(db, simulations=2000).portfolio_var_95),
                "internal_liquidity_benchmark": str(calculate_liquidity_transfer_pricing(db).benchmark_rate),
                "historical_market_var_95": str(calculate_historical_market_risk(db).portfolio_var),
                "liquidity_survival_days": calculate_liquidity_survival_horizon(db).survival_horizon_days,
                "funding_top_lender_share": str(calculate_funding_concentration(db).top_lender_share),
                "risk_limit_status": evaluate_treasury_risk_limits(db).overall_status,
                "balance_sheet_twin_state": run_balance_sheet_twin(db).status,
                "structural_cash_floor": str(calculate_structural_liquidity_gap(db).minimum_cumulative_cash_before_facilities),
                "rate_cash_impact_100bps": str(calculate_interest_rate_gap_dv01(db).annual_cash_impact_100bps),
                "early_warning_status": calculate_early_warning_indicators(db).overall_status,
                "predictive_risk_radar": calculate_treasury_risk_radar(db).overall_status,
                "deterioration_score": str(calculate_treasury_risk_radar(db).deterioration_score),
                "optimal_liquidity_buffer": str(calculate_optimal_liquidity_buffer(db).recommended_buffer),
                "strategic_plan": optimize_strategic_treasury(db).selected_strategy_code,
            },
        }
        selected = self.multi_agent.select_agents(summary.findings, normalized)
        raw = await self.multi_agent.analyze(question, summary.findings, shared, normalized)
        insights = [SpecialistAIInsight(**item) for item in raw]
        return MultiAgentAnalysisResponse(
            mode=normalized,
            selected_agents=selected,
            insights=insights,
            deterministic_summary=summary,
        )

    async def answer(self, db: Session, question: str, include_market_stress: bool = True) -> TreasuryCopilotResponse:
        summary = self.run(db, write_audit=True)
        liquidity = calculate_global_liquidity(db)
        forecast = calculate_liquidity_forecast(db, "BASE")
        severe = calculate_liquidity_forecast(db, "SEVERE")
        derivatives = derivative_risk_summary(db)

        context = {
            "reporting_currency": liquidity.reporting_currency,
            "liquidity": {
                "deployable_cash": str(liquidity.deployable_cash),
                "undrawn_credit": str(liquidity.undrawn_credit),
                "headroom": str(liquidity.liquidity_headroom),
                "local_deficits": [
                    x.entity_name for x in liquidity.entities if x.liquidity_headroom_reporting < 0
                ],
            },
            "forecast": {
                "base_ending_headroom": str(forecast.ending_liquidity_headroom),
                "base_first_breach_week": forecast.first_buffer_breach_week,
                "severe_first_breach_week": severe.first_buffer_breach_week,
                "severe_maximum_shortfall": str(severe.maximum_shortfall),
            },
            "derivatives": {
                "open_trade_count": derivatives.open_trade_count,
                "net_mtm": str(derivatives.net_market_value_reporting),
                "unmapped_trade_count": derivatives.unmapped_trade_count,
            },
            "global_treasury": {
                "trapped_cash": str(calculate_cash_mobility(db).total_trapped_cash),
                "transferable_surplus": str(calculate_cash_mobility(db).total_transferable_surplus),
                "stressed_collateral_call": str(calculate_collateral_liquidity(db).stressed_margin_call),
                "debt_due_180d": str(calculate_refinancing_risk(db).debt_due_180d),
            },
            "execution_controls": self._control_context(db),
            "optimization": {
                "incremental_hedge_reporting": str(optimize_fx_hedges(db).total_incremental_hedge_reporting),
                "tail_funding_need": str(optimize_funding(db).requested_funding_need),
                "tail_funding_uncovered": str(optimize_funding(db).uncovered_funding),
                "optimization_is_advisory": True,
                "historical_market_var_95": str(calculate_historical_market_risk(db).portfolio_var),
                "xva_style_total": str(calculate_xva_style_adjustments(db).total_xva_style_adjustment),
                "survival_horizon_days": calculate_liquidity_survival_horizon(db).survival_horizon_days,
                "funding_top_lender_share": str(calculate_funding_concentration(db).top_lender_share),
                "risk_limit_status": evaluate_treasury_risk_limits(db).overall_status,
                "balance_sheet_twin_state": run_balance_sheet_twin(db).status,
                "structural_cash_floor": str(calculate_structural_liquidity_gap(db).minimum_cumulative_cash_before_facilities),
                "rate_cash_impact_100bps": str(calculate_interest_rate_gap_dv01(db).annual_cash_impact_100bps),
                "contingency_funding_status": build_contingency_funding_plan(db).status,
                "early_warning_status": calculate_early_warning_indicators(db).overall_status,
                "predictive_risk_radar": calculate_treasury_risk_radar(db).overall_status,
                "deterioration_score": str(calculate_treasury_risk_radar(db).deterioration_score),
                "optimal_liquidity_buffer": str(calculate_optimal_liquidity_buffer(db).recommended_buffer),
                "strategic_plan": optimize_strategic_treasury(db).selected_strategy_code,
            },
            "forecast_quality": {
                "accuracy_status": calculate_forecast_accuracy(db).status,
                "cash_bias_pct": str(calculate_forecast_accuracy(db).cash_bias_pct),
                "working_capital_ccc_days": str(calculate_working_capital_cycle(db).group_ccc_days),
                "overdue_receivables_share": str(calculate_receivables_aging(db).overdue_share),
            },
            "agent_findings": [f.model_dump() for f in summary.findings],
        }
        if include_market_stress:
            stress = calculate_market_stress(db)
            context["market_stress"] = {
                "fx_adverse_change": str(stress.estimated_fx_adverse_change),
                "annual_rate_cash_impact": str(stress.annual_rate_cash_impact),
                "near_term_negative_mtm": str(stress.near_term_derivative_negative_mtm),
                "combined_market_liquidity_call": str(stress.combined_market_liquidity_call),
            }

        system_instruction = (
            "You are the synthesis layer of an enterprise multinational treasury-risk system. "
            "Prioritize liquidity survival, funding capacity, market-risk hedging, counterparty risk, policy compliance, and decision traceability. "
            "Never recalculate or replace deterministic values. Never recommend speculative derivatives. "
            "Explicitly identify data/control limitations. Material actions require human approval."
        )
        astra = await self.reasoner.explain(AstraRequest(
            task=question,
            system_instruction=system_instruction,
            validated_context=context,
        ))
        return TreasuryCopilotResponse(
            model=astra.model,
            llm_enabled=astra.enabled,
            answer=astra.text,
            deterministic_summary=summary,
            provider_response_id=astra.response_id,
            error=astra.error,
        )
