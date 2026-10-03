from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field
from typing import Any


class EntityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    country_code: str
    functional_currency: str
    reporting_currency: str
    minimum_cash: Decimal
    is_treasury_centre: bool


class LiquidityComponent(BaseModel):
    entity_id: int
    entity_name: str
    local_currency: str
    reporting_currency: str
    gross_cash_local: Decimal
    restricted_cash_local: Decimal
    committed_outflows_local: Decimal
    deployable_cash_local: Decimal
    minimum_cash_local: Decimal
    undrawn_credit_local: Decimal
    deployable_cash_reporting: Decimal
    minimum_cash_reporting: Decimal
    undrawn_credit_reporting: Decimal
    liquidity_headroom_reporting: Decimal


class GlobalLiquidityOut(BaseModel):
    reporting_currency: str
    gross_cash: Decimal
    restricted_cash: Decimal
    committed_outflows: Decimal
    deployable_cash: Decimal
    minimum_cash: Decimal
    undrawn_credit: Decimal
    liquidity_headroom: Decimal
    data_as_of: datetime
    entities: list[LiquidityComponent]
    warnings: list[str]


class FXExposureRow(BaseModel):
    currency: str
    cash: Decimal
    receivables: Decimal
    payables: Decimal
    derivative_hedge: Decimal
    residual_exposure: Decimal


class AgentFinding(BaseModel):
    agent: str
    severity: str
    title: str
    message: str
    metric: str | None = None


class TreasurySummary(BaseModel):
    ai_model: str
    overall_status: str
    findings: list[AgentFinding]


class ForecastPoint(BaseModel):
    week: int
    week_start: date
    week_end: date
    opening_cash: Decimal
    expected_inflows: Decimal
    expected_outflows: Decimal
    closing_cash: Decimal
    available_facility: Decimal
    minimum_buffer: Decimal
    liquidity_headroom: Decimal
    shortfall: Decimal


class LiquidityForecastOut(BaseModel):
    scenario: str
    scenario_label: str
    reporting_currency: str
    start_date: date
    weeks: int
    receivable_multiplier: Decimal
    payable_multiplier: Decimal
    facility_availability: Decimal
    first_buffer_breach_week: int | None
    maximum_shortfall: Decimal
    ending_cash: Decimal
    ending_liquidity_headroom: Decimal
    points: list[ForecastPoint]
    warnings: list[str]


class StressScenarioSummary(BaseModel):
    scenario: str
    scenario_label: str
    ending_cash: Decimal
    minimum_headroom: Decimal
    maximum_shortfall: Decimal
    first_buffer_breach_week: int | None


class DerivativePositionOut(BaseModel):
    id: int
    entity_name: str
    instrument_type: str
    counterparty: str
    exposure_currency: str
    notional: Decimal
    notional_reporting: Decimal
    hedge_direction: str
    maturity_date: date
    days_to_maturity: int
    market_value_reporting_ccy: Decimal
    hedge_designation: str | None
    underlying_reference: str | None
    mapped_to_underlying: bool


class DerivativeMaturityBucket(BaseModel):
    bucket: str
    notional_reporting: Decimal
    market_value_reporting_ccy: Decimal
    trade_count: int


class DerivativeRiskSummary(BaseModel):
    reporting_currency: str
    open_trade_count: int
    total_notional_reporting: Decimal
    net_market_value_reporting: Decimal
    positive_market_value_reporting: Decimal
    negative_market_value_reporting: Decimal
    unmapped_trade_count: int
    maturity_buckets: list[DerivativeMaturityBucket]
    warnings: list[str]


class HedgeCoverageRow(BaseModel):
    currency: str
    underlying_exposure: Decimal
    hedge_notional: Decimal
    hedge_ratio: Decimal | None
    residual_exposure: Decimal
    policy_min: Decimal
    policy_max: Decimal
    status: str


class CounterpartyExposureRow(BaseModel):
    counterparty: str
    credit_rating: str | None
    current_positive_mtm: Decimal
    potential_future_exposure: Decimal
    credit_exposure: Decimal
    exposure_limit: Decimal
    utilization: Decimal
    status: str


class InterestRateRiskOut(BaseModel):
    reporting_currency: str
    total_debt: Decimal
    fixed_rate_debt: Decimal
    floating_rate_debt: Decimal
    pay_fixed_swap_notional: Decimal
    residual_floating_exposure: Decimal
    floating_share_before_hedges: Decimal
    floating_share_after_hedges: Decimal
    annual_cash_impact_100bps: Decimal
    annual_cash_impact_200bps: Decimal
    warnings: list[str]


class FXStressRow(BaseModel):
    currency: str
    residual_exposure_local: Decimal
    residual_exposure_reporting: Decimal
    adverse_shock_pct: Decimal
    estimated_adverse_value_change: Decimal


class MarketStressOut(BaseModel):
    reporting_currency: str
    fx_shock_pct: Decimal
    rate_shock_bps: int
    estimated_fx_adverse_change: Decimal
    annual_rate_cash_impact: Decimal
    near_term_derivative_negative_mtm: Decimal
    combined_market_liquidity_call: Decimal
    fx_rows: list[FXStressRow]
    warnings: list[str]


class AgentRuntimeStatus(BaseModel):
    model: str
    llm_enabled: bool
    top_level_agents: list[str] = Field(default_factory=list)
    specialist_agents: list[str]
    deterministic_engines: list[str]
    controls: list[str]


class TreasuryCopilotRequest(BaseModel):
    question: str
    include_market_stress: bool = True


class TreasuryCopilotResponse(BaseModel):
    model: str
    llm_enabled: bool
    answer: str | None
    deterministic_summary: TreasurySummary
    provider_response_id: str | None = None
    error: str | None = None


class MTMUpdate(BaseModel):
    trade_id: int
    market_value_reporting_ccy: Decimal
    source: str = "MARKET_DATA"


class MTMUpdateRequest(BaseModel):
    updates: list[MTMUpdate]
    actor: str = "TREASURY_MARKET_DATA"


class MTMUpdateResult(BaseModel):
    updated_trade_ids: list[int]
    audit_event_id: int


class MultiAgentAnalysisRequest(BaseModel):
    question: str
    mode: str = "SELECTIVE"


class SpecialistAIInsight(BaseModel):
    agent: str
    model: str
    enabled: bool
    text: str | None = None
    response_id: str | None = None
    error: str | None = None


class MultiAgentAnalysisResponse(BaseModel):
    mode: str
    selected_agents: list[str]
    insights: list[SpecialistAIInsight]
    deterministic_summary: TreasurySummary


class CashMobilityEntity(BaseModel):
    entity_id: int
    entity_name: str
    country_code: str
    reporting_currency: str
    deployable_cash_reporting: Decimal
    minimum_cash_reporting: Decimal
    extra_restrictions_reporting: Decimal
    transferable_surplus_reporting: Decimal
    local_cash_deficit_reporting: Decimal
    trapped_cash_reporting: Decimal
    restriction_reasons: list[str]


class CashMobilityOut(BaseModel):
    reporting_currency: str
    total_deployable_cash: Decimal
    total_trapped_cash: Decimal
    total_transferable_surplus: Decimal
    total_local_cash_deficit: Decimal
    entities: list[CashMobilityEntity]
    warnings: list[str]


class CashPoolMemberStatus(BaseModel):
    entity_name: str
    pool_currency: str
    deployable_pool_cash: Decimal
    sweep_target: Decimal
    contribution_capacity: Decimal
    funding_need: Decimal


class CashPoolSummary(BaseModel):
    pool_name: str
    pool_type: str
    currency: str
    header_entity: str
    total_contribution_capacity: Decimal
    total_funding_need: Decimal
    internal_offset_capacity: Decimal
    members: list[CashPoolMemberStatus]
    warnings: list[str]


class CrossBorderFundingOption(BaseModel):
    facility_id: int
    lender_entity: str
    borrower_entity: str
    lender_country: str
    borrower_country: str
    currency: str
    available_amount: Decimal
    available_amount_reporting: Decimal
    interest_rate: Decimal
    transfer_pricing_min_rate: Decimal | None
    transfer_pricing_max_rate: Decimal | None
    transfer_pricing_status: str
    withholding_tax_rate: Decimal | None
    estimated_annual_interest_reporting: Decimal
    estimated_annual_withholding_tax_reporting: Decimal | None
    tax_rule_status: str
    maturity_date: date


class CollateralExposureRow(BaseModel):
    counterparty: str
    net_mtm_reporting: Decimal
    threshold_reporting: Decimal
    minimum_transfer_amount_reporting: Decimal
    collateral_posted_reporting: Decimal
    collateral_received_reporting: Decimal
    current_margin_call_reporting: Decimal
    stressed_margin_call_reporting: Decimal
    status: str


class CollateralLiquidityOut(BaseModel):
    reporting_currency: str
    current_margin_call: Decimal
    stressed_margin_call: Decimal
    rows: list[CollateralExposureRow]
    warnings: list[str]


class CovenantStatusRow(BaseModel):
    debt_position_id: int
    lender: str
    covenant_code: str
    metric_name: str
    current_value: Decimal
    threshold_value: Decimal
    direction: str
    headroom_pct: Decimal
    testing_date: date
    status: str


class RefinancingBucket(BaseModel):
    bucket: str
    debt_maturing_reporting: Decimal
    facility_maturing_reporting: Decimal


class RefinancingRiskOut(BaseModel):
    reporting_currency: str
    debt_due_90d: Decimal
    debt_due_180d: Decimal
    debt_due_365d: Decimal
    committed_facilities_due_90d: Decimal
    liquidity_headroom: Decimal
    debt_due_365d_to_headroom: Decimal | None
    maturity_buckets: list[RefinancingBucket]
    covenants: list[CovenantStatusRow]
    warnings: list[str]


class UserAccessOut(BaseModel):
    username: str
    display_name: str
    role: str
    permissions: list[str]


class MarketDataFeedStatus(BaseModel):
    feed_name: str
    asset_class: str
    source_type: str
    status: str
    age_minutes: int
    stale_after_minutes: int
    stale: bool
    execution_usable: bool


class ConnectorStatusOut(BaseModel):
    connector_name: str
    connector_type: str
    system_name: str
    status: str
    age_minutes: int
    stale_after_minutes: int
    stale: bool
    execution_usable: bool
    owner: str


class ReconciliationOut(BaseModel):
    id: int
    connector_name: str
    run_type: str
    source_total: Decimal
    target_total: Decimal
    difference: Decimal
    unmatched_count: int
    status: str
    run_at: datetime


class HedgeAccountingOut(BaseModel):
    designation_id: int
    derivative_position_id: int
    instrument_type: str
    counterparty: str
    designation_type: str
    hedged_item_reference: str
    risk_component: str
    hedge_ratio: Decimal
    documentation_status: str
    effectiveness_status: str
    designation_date: date
    last_tested_at: datetime | None
    accounting_standard: str
    control_status: str


class ControlCheck(BaseModel):
    code: str
    status: str
    severity: str
    message: str


class TransactionProposalCreate(BaseModel):
    proposal_type: str
    source_entity_id: int | None = None
    target_entity_id: int | None = None
    counterparty: str | None = None
    currency: str
    amount: Decimal
    purpose: str
    underlying_reference: str | None = None


class ApprovalRequest(BaseModel):
    decision: str = "APPROVE"
    comment: str = ""


class ExecutionRequest(BaseModel):
    release_note: str = ""


class ApprovalDecisionOut(BaseModel):
    actor: str
    actor_role: str
    decision: str
    comment: str
    created_at: datetime


class TransactionProposalOut(BaseModel):
    id: int
    proposal_type: str
    source_entity_id: int | None
    target_entity_id: int | None
    counterparty: str | None
    currency: str
    amount: Decimal
    amount_reporting: Decimal
    purpose: str
    underlying_reference: str | None
    created_by: str
    created_at: datetime
    status: str
    control_status: str
    required_approvals: int
    approval_count: int
    executed_at: datetime | None
    checks: list[ControlCheck]
    approvals: list[ApprovalDecisionOut]


class ScenarioTemplateOut(BaseModel):
    scenario_code: str
    label: str
    receivable_multiplier: Decimal
    payable_multiplier: Decimal
    facility_availability: Decimal
    fx_shock_pct: Decimal
    rate_shock_bps: int


class ReverseStressOut(BaseModel):
    reporting_currency: str
    weeks: int
    trigger: str
    receivable_multiplier: Decimal
    collection_haircut_pct: Decimal
    payable_multiplier: Decimal
    facility_availability: Decimal
    first_buffer_breach_week: int | None
    maximum_shortfall: Decimal
    ending_liquidity_headroom: Decimal
    iterations: int


class AuditEventOut(BaseModel):
    id: int
    event_type: str
    actor: str
    details: str
    created_at: datetime


class PaymentPredictionOut(BaseModel):
    cash_flow_id: int
    entity_id: int
    counterparty: str
    currency: str
    amount: Decimal
    due_date: date
    on_time_probability: Decimal
    late_probability: Decimal
    expected_delay_days: Decimal
    p10_delay_days: Decimal
    p90_delay_days: Decimal
    expected_receipt_date: date
    confidence: str


class ModelValidationOut(BaseModel):
    model_code: str
    version: str
    training_rows: int
    validation_rows: int
    mae_delay_days: Decimal
    brier_score: Decimal
    auc: Decimal | None
    validation_status: str
    trained_at: datetime
    data_fingerprint: str


class ModelDriftOut(BaseModel):
    model_code: str
    delay_psi: Decimal
    late_rate_baseline: Decimal
    late_rate_recent: Decimal
    mean_delay_baseline: Decimal
    mean_delay_recent: Decimal
    status: str
    notes: list[str]


class ModelRegistryOut(BaseModel):
    model_code: str
    version: str
    model_type: str
    trained_at: datetime
    training_rows: int
    validation_status: str
    metrics_json: str
    feature_schema: str
    data_fingerprint: str
    owner: str


class MLForecastPoint(BaseModel):
    week: int
    week_start: date
    week_end: date
    expected_inflows: Decimal
    conservative_inflows: Decimal
    optimistic_inflows: Decimal
    expected_outflows: Decimal
    expected_closing_cash: Decimal
    conservative_closing_cash: Decimal
    optimistic_closing_cash: Decimal
    expected_headroom: Decimal
    conservative_headroom: Decimal
    optimistic_headroom: Decimal


class MLCashForecastOut(BaseModel):
    reporting_currency: str
    model_code: str
    version: str
    validation_status: str
    first_conservative_breach_week: int | None
    expected_ending_headroom: Decimal
    conservative_ending_headroom: Decimal
    optimistic_ending_headroom: Decimal
    points: list[MLForecastPoint]
    payment_predictions: list[PaymentPredictionOut]
    warnings: list[str]


class IntradayPaymentPriorityOut(BaseModel):
    payment_reference: str
    counterparty: str
    direction: str
    payment_type: str
    amount_reporting: Decimal
    scheduled_at: datetime
    priority_score: int
    recommended_action: str
    anomaly_flag: bool


class IntradayBucketOut(BaseModel):
    label: str
    start_hour: int
    end_hour: int
    inflows: Decimal
    outflows: Decimal
    net_flow: Decimal
    projected_balance: Decimal
    minimum_buffer: Decimal
    headroom: Decimal


class IntradayLiquidityOut(BaseModel):
    reporting_currency: str
    entity_id: int
    entity_name: str
    opening_deployable_cash: Decimal
    minimum_buffer: Decimal
    available_committed_facility: Decimal
    lowest_projected_balance: Decimal
    peak_intraday_funding_need: Decimal
    first_buffer_breach_bucket: str | None
    buckets: list[IntradayBucketOut]
    payment_priorities: list[IntradayPaymentPriorityOut]
    warnings: list[str]


class PaymentAnomalyOut(BaseModel):
    payment_reference: str
    counterparty: str
    payment_type: str
    amount_reporting: Decimal
    scheduled_at: datetime
    anomaly_score: Decimal
    severity: str
    reasons: list[str]


class IPVTradeOut(BaseModel):
    derivative_position_id: int
    instrument_type: str
    counterparty: str
    book_mtm_reporting: Decimal
    independent_mid_reporting: Decimal | None
    absolute_deviation: Decimal | None
    deviation_pct: Decimal | None
    independent_source_count: int
    latest_observed_at: datetime | None
    status: str


class IPVSummaryOut(BaseModel):
    reporting_currency: str
    pass_count: int
    warning_count: int
    fail_count: int
    missing_count: int
    rows: list[IPVTradeOut]
    warnings: list[str]


class MarketDataFallbackOut(BaseModel):
    asset_class: str
    selected_feed: str | None
    source_type: str | None
    age_minutes: int | None
    fallback_used: bool
    execution_usable: bool
    reason: str


class PaymentScreeningOut(BaseModel):
    payment_reference: str
    counterparty: str
    provider: str
    status: str
    screened_at: datetime
    list_version: str
    reason: str
    execution_blocked: bool


class IntegratedScenarioRequest(BaseModel):
    label: str = "User integrated scenario"
    weeks: int = 13
    receivable_multiplier: Decimal = Decimal("0.80")
    payable_multiplier: Decimal = Decimal("1.10")
    facility_availability: Decimal = Decimal("0.70")
    fx_shock_pct: Decimal = Decimal("0.10")
    rate_shock_bps: int = 200
    collateral_stress_multiplier: Decimal = Decimal("1.00")
    refinancing_spread_shock_bps: int = 150


class IntegratedScenarioOut(BaseModel):
    label: str
    reporting_currency: str
    weeks: int
    forecast_ending_headroom: Decimal
    forecast_maximum_shortfall: Decimal
    first_buffer_breach_week: int | None
    fx_economic_value_sensitivity: Decimal
    rate_cash_impact_horizon: Decimal
    derivative_or_collateral_liquidity_call: Decimal
    incremental_refinancing_cost_horizon: Decimal
    stressed_liquidity_headroom_after_overlays: Decimal
    status: str
    component_notes: list[str]


class InstitutionalValuationTradeOut(BaseModel):
    derivative_position_id: int
    instrument_type: str
    counterparty: str
    model_type: str
    model_value_reporting: Decimal
    book_value_reporting: Decimal
    valuation_difference: Decimal
    source_quality: str
    model_status: str
    inputs_as_of: datetime


class InstitutionalValuationOut(BaseModel):
    reporting_currency: str
    total_model_value: Decimal
    total_book_value: Decimal
    aggregate_difference: Decimal
    priced_trade_count: int
    unpriced_trade_count: int
    rows: list[InstitutionalValuationTradeOut]
    warnings: list[str]


class LiquidityAtRiskOut(BaseModel):
    reporting_currency: str
    horizon_weeks: int
    confidence: Decimal
    simulations: int
    expected_ending_headroom: Decimal
    p05_ending_headroom: Decimal
    p01_ending_headroom: Decimal
    cash_flow_at_risk: Decimal
    liquidity_at_risk: Decimal
    probability_of_buffer_breach: Decimal
    expected_funding_need: Decimal
    tail_funding_need: Decimal
    seed: int
    methodology: str
    warnings: list[str]


class NettingSetExposureOut(BaseModel):
    netting_set_code: str
    counterparty: str
    close_out_netting_enforceable: bool
    legal_opinion_status: str
    gross_positive_mtm: Decimal
    gross_negative_mtm: Decimal
    net_mtm: Decimal
    netting_benefit: Decimal
    collateral_posted: Decimal
    collateral_received: Decimal
    exposure_after_netting_and_collateral: Decimal
    trade_count: int
    status: str


class NettingSummaryOut(BaseModel):
    reporting_currency: str
    gross_credit_exposure: Decimal
    net_credit_exposure: Decimal
    total_netting_benefit: Decimal
    legally_enforceable_sets: int
    review_required_sets: int
    rows: list[NettingSetExposureOut]
    warnings: list[str]


class CollateralOptimizationRow(BaseModel):
    counterparty: str
    netting_set_code: str
    eligible_currency: str
    additional_collateral_required: Decimal
    same_currency_available: Decimal
    cross_currency_funding_required: Decimal
    recommended_source_entity: str | None
    status: str


class CollateralOptimizationOut(BaseModel):
    reporting_currency: str
    total_additional_collateral_required: Decimal
    total_cross_currency_funding_required: Decimal
    rows: list[CollateralOptimizationRow]
    warnings: list[str]


class ChampionChallengerOut(BaseModel):
    model_code: str
    champion_version: str
    challenger_version: str
    champion_mae: Decimal
    challenger_mae: Decimal
    champion_brier: Decimal
    challenger_brier: Decimal
    mae_improvement_pct: Decimal
    brier_improvement_pct: Decimal
    promotion_threshold_pct: Decimal
    recommendation: str
    auto_promotion_allowed: bool
    governance_note: str


class ResilienceComponentOut(BaseModel):
    component_name: str
    criticality_tier: str
    rto_minutes: int
    rpo_minutes: int
    multi_region: bool
    last_dr_test_at: datetime | None
    last_dr_test_result: str
    status: str


class OperationalResilienceOut(BaseModel):
    overall_status: str
    tier1_count: int
    tier1_gaps: int
    components: list[ResilienceComponentOut]
    warnings: list[str]


class SecurityPostureOut(BaseModel):
    environment: str
    auth_mode: str
    production_identity_ready: bool
    demo_identity_blocked_in_production: bool
    database_backend: str
    tls_expected: bool
    secrets_in_environment_only: bool
    write_idempotency_required_in_production: bool
    security_headers_enabled: bool
    status: str
    warnings: list[str]


class TreasuryEventIn(BaseModel):
    source_system: str
    connector_name: str
    event_type: str
    idempotency_key: str
    event_time: datetime
    payload: dict[str, Any]
    entity_id: int | None = None
    external_reference: str | None = None
    sequence_no: int | None = None
    schema_version: str = "1.0"


class TreasuryEventOut(BaseModel):
    id: int
    source_system: str
    connector_name: str
    event_type: str
    idempotency_key: str
    event_time: datetime
    received_at: datetime
    entity_id: int | None
    external_reference: str | None
    sequence_no: int | None
    schema_version: str
    payload_hash: str
    processing_status: str
    processing_error: str
    replay_count: int


class EventIngestionResult(BaseModel):
    event: TreasuryEventOut
    duplicate: bool
    projected: bool
    alert_ids: list[int] = Field(default_factory=list)


class ConnectorCheckpointOut(BaseModel):
    connector_name: str
    source_system: str
    last_sequence_no: int | None
    last_event_time: datetime | None
    last_received_at: datetime | None
    lag_seconds: int | None
    accepted_count: int
    duplicate_count: int
    quarantined_count: int
    failed_count: int
    status: str


class LiveTreasuryAlertOut(BaseModel):
    id: int
    alert_key: str
    category: str
    severity: str
    title: str
    message: str
    source_event_id: int | None
    status: str
    created_at: datetime
    last_seen_at: datetime
    acknowledged_by: str | None
    acknowledged_at: datetime | None


class AlertAcknowledgementRequest(BaseModel):
    comment: str = ""


class LiveOperationsStatusOut(BaseModel):
    status: str
    events_24h: int
    applied_24h: int
    quarantined_24h: int
    failed_24h: int
    duplicate_events: int
    max_event_lag_seconds: int
    open_alerts: int
    critical_alerts: int
    last_event_received_at: datetime | None
    checkpoints: list[ConnectorCheckpointOut]
    warnings: list[str]


class LiveMonitorRunOut(BaseModel):
    status: str
    alerts_created_or_refreshed: int
    open_alerts: int
    critical_alerts: int
    liquidity_headroom: Decimal
    lar_buffer_breach_probability: Decimal
    intraday_peak_funding_need: Decimal
    notes: list[str]


class ExecutionMessageCreate(BaseModel):
    connector_name: str
    idempotency_key: str


class ExecutionMessageOut(BaseModel):
    id: int
    message_id: str
    proposal_id: int
    connector_name: str
    idempotency_key: str
    payload_hash: str
    signature: str
    status: str
    created_by: str
    created_at: datetime
    sent_at: datetime | None
    acknowledged_at: datetime | None
    external_reference: str | None
    acknowledgement_detail: str


class ExecutionAcknowledgementRequest(BaseModel):
    status: str
    external_reference: str | None = None
    detail: str = ""


class EventReplayResult(BaseModel):
    event_id: int
    replay_count: int
    processing_status: str
    processing_error: str
    projected: bool

# MVP-9: Global Treasury Optimization & Decision Intelligence
class HedgeOptimizationRequest(BaseModel):
    target_hedge_ratio: Decimal = Decimal("0.75")
    option_share: Decimal = Decimal("0.25")
    fx_shock_pct: Decimal = Decimal("0.10")
    forward_cost_bps: Decimal = Decimal("12")
    option_premium_pct: Decimal = Decimal("0.0125")


class HedgeOptimizationRow(BaseModel):
    currency: str
    underlying_exposure: Decimal
    current_hedge_notional: Decimal
    current_hedge_ratio: Decimal | None
    policy_min: Decimal
    policy_max: Decimal
    target_hedge_ratio: Decimal
    incremental_hedge_notional: Decimal
    forward_notional: Decimal
    option_notional: Decimal
    residual_exposure_after: Decimal
    adverse_value_sensitivity_after: Decimal
    estimated_execution_liquidity_cost: Decimal
    action: str
    status: str


class HedgeOptimizationOut(BaseModel):
    reporting_currency: str
    target_hedge_ratio: Decimal
    total_incremental_hedge_reporting: Decimal
    estimated_execution_liquidity_cost_reporting: Decimal
    rows: list[HedgeOptimizationRow]
    assumptions: list[str]
    warnings: list[str]


class FundingAllocationRow(BaseModel):
    source_type: str
    source_name: str
    capacity_reporting: Decimal
    allocated_reporting: Decimal
    estimated_annual_cost_reporting: Decimal | None
    cost_rate: Decimal | None
    control_status: str
    notes: str


class FundingOptimizationOut(BaseModel):
    reporting_currency: str
    requested_funding_need: Decimal
    covered_funding: Decimal
    uncovered_funding: Decimal
    internal_cash_mobilization_cap: Decimal
    rows: list[FundingAllocationRow]
    intercompany_structuring_options: list[CrossBorderFundingOption]
    warnings: list[str]


class CashSweepInstruction(BaseModel):
    pool_name: str
    from_entity: str
    to_entity: str
    currency: str
    amount: Decimal
    status: str


class CashPoolOptimizationOut(BaseModel):
    total_internal_offset: Decimal
    instruction_count: int
    instructions: list[CashSweepInstruction]
    warnings: list[str]


class ScenarioSearchRow(BaseModel):
    rank: int
    receivable_multiplier: Decimal
    payable_multiplier: Decimal
    facility_availability: Decimal
    fx_shock_pct: Decimal
    rate_shock_bps: int
    stressed_headroom: Decimal
    maximum_shortfall: Decimal
    first_buffer_breach_week: int | None
    status: str


class ScenarioSearchOut(BaseModel):
    reporting_currency: str
    combinations_tested: int
    breach_count: int
    worst_stressed_headroom: Decimal
    rows: list[ScenarioSearchRow]
    methodology: str
    warnings: list[str]


class TreasuryStrategyRow(BaseModel):
    strategy_code: str
    description: str
    hedge_target_ratio: Decimal
    cash_mobilization_pct: Decimal
    contingency_prefunding_pct: Decimal
    tail_funding_target: Decimal
    projected_internal_cash_use: Decimal
    projected_external_capacity_use: Decimal
    residual_unfunded_tail: Decimal
    estimated_hedge_execution_cost: Decimal
    policy_exception_count: int
    resilience_score: Decimal
    decision_status: str


class TreasuryDecisionPackOut(BaseModel):
    reporting_currency: str
    decision_objective: str
    recommended_strategy_code: str
    strategies: list[TreasuryStrategyRow]
    scenario_search: ScenarioSearchOut
    human_approval_required: bool
    execution_authority: str
    decision_notes: list[str]

# MVP-10: Treasury Digital Twin & Enterprise Risk Intelligence
class MarketRiskCurrencyRow(BaseModel):
    currency: str
    residual_exposure_local: Decimal
    residual_exposure_reporting: Decimal
    annualized_volatility: Decimal
    var_95: Decimal
    expected_shortfall_95: Decimal
    data_status: str


class MarketRiskDistributionOut(BaseModel):
    reporting_currency: str
    horizon_days: int
    confidence: Decimal
    simulations: int
    portfolio_var_95: Decimal
    portfolio_expected_shortfall_95: Decimal
    earnings_at_risk_95_90d: Decimal
    rows: list[MarketRiskCurrencyRow]
    methodology: str
    warnings: list[str]


class LiquidityTransferPricingRow(BaseModel):
    entity_id: int
    entity_name: str
    liquidity_position_reporting: Decimal
    position_type: str
    internal_rate: Decimal
    annual_internal_charge_or_credit: Decimal
    status: str


class LiquidityTransferPricingOut(BaseModel):
    reporting_currency: str
    benchmark_rate: Decimal
    surplus_credit_rate: Decimal
    deficit_charge_rate: Decimal
    net_internal_charge: Decimal
    rows: list[LiquidityTransferPricingRow]
    methodology: str
    warnings: list[str]


class BankAccountRationalizationRow(BaseModel):
    account_id: int
    entity_name: str
    bank_name: str
    country_code: str
    currency: str
    deployable_balance_reporting: Decimal
    restricted_ratio: Decimal
    age_hours: int
    role: str
    recommendation: str
    rationale: str


class BankAccountRationalizationOut(BaseModel):
    reporting_currency: str
    account_count: int
    bank_count: int
    stale_account_count: int
    review_candidate_count: int
    largest_bank: str | None
    largest_bank_share: Decimal
    rows: list[BankAccountRationalizationRow]
    warnings: list[str]


class DigitalTwinScenarioRequest(BaseModel):
    label: str = "Treasury digital twin scenario"
    weeks: int = 13
    receivable_multiplier: Decimal = Decimal("0.85")
    payable_multiplier: Decimal = Decimal("1.10")
    facility_availability: Decimal = Decimal("0.75")
    fx_shock_pct: Decimal = Decimal("0.10")
    rate_shock_bps: int = 200
    collateral_stress_multiplier: Decimal = Decimal("1.00")
    refinancing_spread_shock_bps: int = 150


class DigitalTwinOut(BaseModel):
    twin_version: str
    institutional_depth_version: str = "MVP-11.0"
    reporting_currency: str
    state: str
    base_liquidity_headroom: Decimal
    scenario_stressed_headroom: Decimal
    first_buffer_breach_week: int | None
    liquidity_at_risk_95: Decimal
    cash_flow_at_risk_95: Decimal
    buffer_breach_probability: Decimal
    market_var_95: Decimal
    market_expected_shortfall_95: Decimal
    intraday_peak_funding_need: Decimal
    trapped_cash: Decimal
    stressed_collateral_call: Decimal
    debt_due_180d: Decimal
    historical_market_var_95: Decimal = Decimal("0")
    xva_style_total: Decimal = Decimal("0")
    liquidity_survival_days: int = 0
    funding_top_lender_share: Decimal = Decimal("0")
    treasury_limit_status: str = "NOT_EVALUATED"
    scenario: IntegratedScenarioOut
    actions: list[str]
    assumptions: list[str]
    warnings: list[str]

# MVP-11: Institutional counterparty, funding concentration and survival-risk layer
class HistoricalFactorStat(BaseModel):
    factor_key: str
    observations: int
    annualized_volatility: Decimal
    ewma_volatility: Decimal
    latest_return: Decimal
    data_status: str


class HistoricalCorrelationPair(BaseModel):
    factor_a: str
    factor_b: str
    correlation: Decimal


class HistoricalMarketCalibrationOut(BaseModel):
    lookback_observations: int
    ewma_lambda: Decimal
    factors: list[HistoricalFactorStat]
    correlations: list[HistoricalCorrelationPair]
    source_status: str
    warnings: list[str]


class HistoricalMarketRiskOut(BaseModel):
    reporting_currency: str
    horizon_days: int
    confidence: Decimal
    portfolio_var: Decimal
    expected_shortfall: Decimal
    earnings_at_risk_90d: Decimal
    correlation_method: str
    factor_count: int
    warnings: list[str]


class XVAExposureRow(BaseModel):
    counterparty: str
    netting_set_code: str
    exposure_after_netting_collateral: Decimal
    one_year_pd: Decimal
    lgd: Decimal
    funding_spread_bps: Decimal
    average_maturity_years: Decimal
    cva_style_adjustment: Decimal
    fva_style_adjustment: Decimal
    total_xva_style_adjustment: Decimal
    data_status: str


class XVAOut(BaseModel):
    reporting_currency: str
    cva_style_total: Decimal
    fva_style_total: Decimal
    total_xva_style_adjustment: Decimal
    rows: list[XVAExposureRow]
    methodology: str
    warnings: list[str]


class LiquiditySurvivalOut(BaseModel):
    reporting_currency: str
    horizon_weeks: int
    scenario_label: str
    starting_deployable_cash: Decimal
    starting_available_facilities: Decimal
    minimum_liquidity_buffer: Decimal
    first_buffer_breach_week: int | None
    first_buffer_breach_day_estimate: int | None
    hard_liquidity_depletion_week: int | None
    survival_horizon_days: int
    ending_effective_liquidity: Decimal
    minimum_effective_liquidity: Decimal
    status: str
    warnings: list[str]


class FundingConcentrationRow(BaseModel):
    lender: str
    debt_reporting: Decimal
    committed_facility_reporting: Decimal
    undrawn_facility_reporting: Decimal
    total_funding_capacity_reporting: Decimal
    share_of_total_funding: Decimal
    maturity_within_180d_reporting: Decimal


class FundingConcentrationOut(BaseModel):
    reporting_currency: str
    total_funding_reporting: Decimal
    lender_count: int
    top_lender: str | None
    top_lender_share: Decimal
    top_three_share: Decimal
    hhi: Decimal
    funding_due_180d: Decimal
    rows: list[FundingConcentrationRow]
    warnings: list[str]


class TreasuryRiskLimitStatus(BaseModel):
    limit_code: str
    category: str
    metric_name: str
    comparator: str
    threshold_value: Decimal
    current_value: Decimal
    utilization: Decimal | None
    status: str
    owner: str


class TreasuryRiskLimitFrameworkOut(BaseModel):
    overall_status: str
    breach_count: int
    warning_count: int
    rows: list[TreasuryRiskLimitStatus]
    warnings: list[str]


class DigitalTwinOptimizationRequest(BaseModel):
    objective: str = "LIQUIDITY_RESILIENCE"
    weeks: int = 13


class DigitalTwinOptimizedScenario(BaseModel):
    rank: int
    receivable_multiplier: Decimal
    payable_multiplier: Decimal
    facility_availability: Decimal
    collateral_stress_multiplier: Decimal
    stressed_headroom: Decimal
    first_buffer_breach_week: int | None
    survival_horizon_days: int
    resilience_score: Decimal
    limit_breach_count: int
    status: str


class DigitalTwinOptimizationOut(BaseModel):
    reporting_currency: str
    objective: str
    combinations_tested: int
    selected_scenario_rank: int
    scenarios: list[DigitalTwinOptimizedScenario]
    execution_authority: str
    methodology: str
    warnings: list[str]

# MVP-12: Enterprise liquidity command and predictive balance-sheet intelligence
class StructuralLiquidityBucket(BaseModel):
    bucket: str
    start_day: int
    end_day: int | None
    probability_weighted_inflows: Decimal
    contractual_payables: Decimal
    debt_maturities: Decimal
    net_contractual_gap: Decimal
    cumulative_cash_before_facilities: Decimal
    committed_facility_capacity_expiring: Decimal


class StructuralLiquidityGapOut(BaseModel):
    reporting_currency: str
    opening_deployable_cash: Decimal
    minimum_cash_buffer: Decimal
    minimum_cumulative_cash_before_facilities: Decimal
    rows: list[StructuralLiquidityBucket]
    warnings: list[str]


class InterestRateGapBucket(BaseModel):
    currency: str
    fixed_debt_reporting: Decimal
    floating_debt_reporting: Decimal
    pay_fixed_swap_reporting: Decimal
    receive_fixed_swap_reporting: Decimal
    residual_floating_reporting: Decimal
    debt_dv01_proxy_reporting: Decimal
    swap_dv01_proxy_reporting: Decimal


class InterestRateGapDV01Out(BaseModel):
    reporting_currency: str
    fixed_debt_reporting: Decimal
    floating_debt_reporting: Decimal
    residual_floating_reporting: Decimal
    annual_cash_impact_100bps: Decimal
    debt_dv01_proxy_reporting: Decimal
    swap_dv01_proxy_reporting: Decimal
    combined_dv01_proxy_reporting: Decimal
    rows: list[InterestRateGapBucket]
    warnings: list[str]


class FundingTenorBucket(BaseModel):
    tenor_bucket: str
    target_share: Decimal
    proposed_amount_reporting: Decimal


class FundingTenorOptimizationOut(BaseModel):
    reporting_currency: str
    objective: str
    requested_new_funding: Decimal
    current_funding_due_180d: Decimal
    current_top_lender_share: Decimal
    current_debt_due_180d: Decimal
    rows: list[FundingTenorBucket]
    rationale: str
    execution_authority: str
    warnings: list[str]


class CrossCurrencyFundingCandidate(BaseModel):
    entity_name: str
    country_code: str
    local_currency: str
    funding_need_reporting: Decimal
    candidate_structures: list[str]
    hedge_required_for_group_usd_funding: bool
    pricing_status: str
    tax_regulatory_status: str


class CrossCurrencyFundingOut(BaseModel):
    reporting_currency: str
    candidate_count: int
    candidates: list[CrossCurrencyFundingCandidate]
    decision_status: str
    execution_authority: str
    warnings: list[str]


class ContingencyFundingAction(BaseModel):
    stage: int
    action: str
    available_capacity_reporting: Decimal
    modeled_use_reporting: Decimal
    control_requirements: str


class ContingencyFundingPlanOut(BaseModel):
    reporting_currency: str
    status: str
    reference_tail_funding_need: Decimal
    survival_horizon_days: int
    transferable_cash_capacity: Decimal
    committed_facility_capacity: Decimal
    uncovered_contingency_need: Decimal
    actions: list[ContingencyFundingAction]
    activation_triggers: list[str]
    execution_authority: str
    warnings: list[str]


class EarlyWarningIndicator(BaseModel):
    indicator_code: str
    current_value: Decimal
    amber_threshold: Decimal
    red_threshold: Decimal
    direction: str
    unit: str
    status: str


class EarlyWarningOut(BaseModel):
    overall_status: str
    red_count: int
    amber_count: int
    green_count: int
    indicators: list[EarlyWarningIndicator]
    governed_limit_status: str
    warnings: list[str]


class BalanceSheetTwinRequest(BaseModel):
    label: str = "Balance-sheet treasury stress"
    weeks: int = 13
    receivable_multiplier: Decimal = Decimal("0.80")
    payable_multiplier: Decimal = Decimal("1.10")
    facility_availability: Decimal = Decimal("0.70")
    fx_shock_pct: Decimal = Decimal("0.10")
    rate_shock_bps: int = 200
    collateral_stress_multiplier: Decimal = Decimal("1.00")
    refinancing_spread_shock_bps: int = 150

    def to_integrated(self) -> "IntegratedScenarioRequest":
        return IntegratedScenarioRequest(
            label=self.label,
            weeks=self.weeks,
            receivable_multiplier=self.receivable_multiplier,
            payable_multiplier=self.payable_multiplier,
            facility_availability=self.facility_availability,
            fx_shock_pct=self.fx_shock_pct,
            rate_shock_bps=self.rate_shock_bps,
            collateral_stress_multiplier=self.collateral_stress_multiplier,
            refinancing_spread_shock_bps=self.refinancing_spread_shock_bps,
        )


class BalanceSheetTwinOut(BaseModel):
    version: str
    reporting_currency: str
    scenario_label: str
    status: str
    stressed_liquidity_headroom: Decimal
    structural_cash_floor_before_facilities: Decimal
    survival_horizon_days: int
    first_buffer_breach_week: int | None
    residual_floating_rate_exposure: Decimal
    incremental_rate_cash_impact: Decimal
    fx_economic_value_sensitivity: Decimal
    collateral_or_derivative_liquidity_call: Decimal
    base_digital_twin_state: str
    execution_authority: str
    actions: list[str]
    warnings: list[str]

# MVP-13: Deep liquidity-risk intelligence
class LiquidityConcentrationRow(BaseModel):
    dimension: str
    top_name: str | None
    top_share: Decimal
    hhi: Decimal
    total_reporting: Decimal
    component_count: int


class LiquidityConcentrationOut(BaseModel):
    reporting_currency: str
    deployable_cash: Decimal
    transferable_surplus: Decimal
    trapped_cash: Decimal
    trapped_cash_share: Decimal
    transferability_ratio: Decimal
    rows: list[LiquidityConcentrationRow]
    warnings: list[str]


class ProbabilisticLiquidityWeek(BaseModel):
    week: int
    p05_headroom: Decimal
    median_headroom: Decimal
    p95_headroom: Decimal
    breach_probability: Decimal


class ProbabilisticLiquidityOut(BaseModel):
    reporting_currency: str
    horizon_weeks: int
    simulations: int
    seed: int
    probability_of_any_buffer_breach: Decimal
    expected_first_breach_week_if_breached: Decimal | None
    p05_minimum_headroom: Decimal
    median_minimum_headroom: Decimal
    p95_minimum_headroom: Decimal
    tail_funding_need_95: Decimal
    expected_funding_need: Decimal
    weekly_distribution: list[ProbabilisticLiquidityWeek]
    methodology: str
    warnings: list[str]


class LiquidityAttributionRequest(BaseModel):
    label: str = "Liquidity stress attribution"
    weeks: int = 13
    receivable_multiplier: Decimal = Decimal("0.70")
    payable_multiplier: Decimal = Decimal("1.15")
    facility_availability: Decimal = Decimal("0.60")
    fx_shock_pct: Decimal = Decimal("0.10")
    rate_shock_bps: int = 200
    collateral_stress_multiplier: Decimal = Decimal("1.00")
    refinancing_spread_shock_bps: int = 150


class LiquidityAttributionRow(BaseModel):
    driver: str
    standalone_headroom_impact: Decimal
    direction: str
    liquidity_transmission: str


class LiquidityAttributionOut(BaseModel):
    reporting_currency: str
    label: str
    base_headroom: Decimal
    stressed_headroom: Decimal
    total_deterioration: Decimal
    explained_deterioration: Decimal
    interaction_residual: Decimal
    rows: list[LiquidityAttributionRow]
    warnings: list[str]


class ForecastDriverRow(BaseModel):
    counterparty: str
    flow_type: str
    currency: str
    probability_weighted_reporting: Decimal
    signed_liquidity_impact: Decimal
    share_of_absolute_projected_flows: Decimal


class ForecastDriverOut(BaseModel):
    reporting_currency: str
    horizon_weeks: int
    total_probability_weighted_inflows: Decimal
    total_contractual_outflows: Decimal
    absolute_projected_flow_base: Decimal
    largest_driver_share: Decimal
    top_five_driver_share: Decimal
    rows: list[ForecastDriverRow]
    warnings: list[str]


class LiquidityPlaybookAction(BaseModel):
    priority: int
    action: str
    category: str
    quantified_capacity_reporting: Decimal | None
    lead_time: str
    prerequisites: str
    execution_authority: str


class LiquidityActionPlaybookOut(BaseModel):
    reporting_currency: str
    trigger_status: str
    reference_tail_funding_need: Decimal
    quantified_capacity_total: Decimal
    residual_uncovered_need: Decimal
    actions: list[LiquidityPlaybookAction]
    warnings: list[str]

# MVP-14: Forecast accuracy and working-capital liquidity intelligence
class ForecastAccuracyRow(BaseModel):
    segment_type: str
    segment_value: str
    observation_count: int
    forecast_reporting: Decimal
    actual_reporting: Decimal
    absolute_error_reporting: Decimal
    wape: Decimal
    cash_bias_pct: Decimal


class ForecastAccuracyOut(BaseModel):
    reporting_currency: str
    lookback_days: int
    observation_count: int
    overall_wape: Decimal
    cash_bias_pct: Decimal
    status: str
    rows: list[ForecastAccuracyRow]
    warnings: list[str]


class ForecastBiasEntityRow(BaseModel):
    entity_name: str
    inflow_bias_pct: Decimal
    outflow_bias_pct: Decimal
    cash_bias_pct: Decimal
    observation_count: int
    status: str


class ForecastBiasOut(BaseModel):
    reporting_currency: str
    lookback_days: int
    optimistic_bias_entities: int
    conservative_bias_entities: int
    rows: list[ForecastBiasEntityRow]
    warnings: list[str]


class WorkingCapitalCycleRow(BaseModel):
    entity_name: str
    period_end: date
    revenue_reporting: Decimal
    cogs_reporting: Decimal
    dso_days: Decimal
    dpo_days: Decimal
    dio_days: Decimal
    ccc_days: Decimal
    prior_ccc_days: Decimal | None
    ccc_change_days: Decimal | None


class WorkingCapitalCycleOut(BaseModel):
    reporting_currency: str
    latest_period_end: date
    group_dso_days: Decimal
    group_dpo_days: Decimal
    group_dio_days: Decimal
    group_ccc_days: Decimal
    prior_group_ccc_days: Decimal | None
    group_ccc_change_days: Decimal | None
    rows: list[WorkingCapitalCycleRow]
    warnings: list[str]


class ReceivablesAgingBucket(BaseModel):
    bucket: str
    amount_reporting: Decimal
    probability_weighted_reporting: Decimal
    invoice_count: int


class ReceivablesCounterpartyRisk(BaseModel):
    counterparty: str
    amount_reporting: Decimal
    days_overdue: int
    collection_probability: Decimal


class ReceivablesAgingOut(BaseModel):
    reporting_currency: str
    total_open_receivables: Decimal
    total_overdue_receivables: Decimal
    overdue_share: Decimal
    probability_weighted_open_receivables: Decimal
    buckets: list[ReceivablesAgingBucket]
    top_overdue_counterparties: list[ReceivablesCounterpartyRisk]
    warnings: list[str]


class WorkingCapitalLiquidityBridgeRequest(BaseModel):
    dso_improvement_days: Decimal = Decimal("5")
    dpo_extension_days: Decimal = Decimal("3")
    dio_improvement_days: Decimal = Decimal("5")


class WorkingCapitalLiquidityBridgeOut(BaseModel):
    reporting_currency: str
    current_liquidity_headroom: Decimal
    dso_cash_release: Decimal
    dpo_cash_release: Decimal
    inventory_cash_release: Decimal
    total_modeled_cash_release: Decimal
    pro_forma_liquidity_headroom: Decimal
    execution_authority: str
    warnings: list[str]


# MVP-15 to MVP-20 enterprise completion schemas
class CrossBorderConstraintRow(BaseModel):
    source_country: str
    target_country: str
    transfer_type: str
    currency: str | None
    max_amount_reporting: Decimal | None
    withholding_tax_rate: Decimal
    regulatory_status: str
    legal_status: str
    executable: bool
    blockers: list[str]


class CrossBorderConstraintGraphOut(BaseModel):
    reporting_currency: str
    active_route_count: int
    executable_route_count: int
    blocked_route_count: int
    rows: list[CrossBorderConstraintRow]
    warnings: list[str]


class LiquidityRouteProposal(BaseModel):
    source_entity: str
    target_entity: str
    source_country: str
    target_country: str
    transfer_type: str
    currency: str
    amount_reporting: Decimal
    estimated_withholding_cost: Decimal
    status: str
    blockers: list[str]


class LegalEntityLiquidityOptimizationOut(BaseModel):
    reporting_currency: str
    transferable_surplus: Decimal
    local_deficit: Decimal
    proposed_transfer: Decimal
    unresolved_deficit: Decimal
    routes: list[LiquidityRouteProposal]
    execution_authority: str
    warnings: list[str]


class ConnectorReadinessRow(BaseModel):
    connector_code: str
    connector_type: str
    system_name: str
    environment: str
    status: str
    last_success_at: datetime | None
    latency_ms: Decimal | None
    error_rate: Decimal
    supports_idempotency: bool
    supports_reconciliation: bool
    readiness: str
    gaps: list[str]


class ConnectorReadinessOut(BaseModel):
    ready_count: int
    degraded_count: int
    blocked_count: int
    rows: list[ConnectorReadinessRow]
    canonical_contract_version: str
    warnings: list[str]


class EnterpriseSecurityControlRow(BaseModel):
    control_code: str
    domain: str
    status: str
    required: bool
    owner: str
    evidence: str
    age_days: int | None


class EnterpriseSecurityPostureOut(BaseModel):
    environment: str
    overall_status: str
    required_controls: int
    passing_controls: int
    failing_controls: int
    coverage_pct: Decimal
    rows: list[EnterpriseSecurityControlRow]
    warnings: list[str]


class ModelValidationRow(BaseModel):
    model_code: str
    validation_type: str
    metric_name: str
    metric_value: Decimal
    threshold_value: Decimal
    comparison: str
    status: str
    validated_by: str
    created_at: datetime


class ModelValidationDashboardOut(BaseModel):
    model_count: int
    validation_count: int
    pass_count: int
    watch_count: int
    fail_count: int
    production_blocked_models: list[str]
    rows: list[ModelValidationRow]
    warnings: list[str]


class RoleWorkQueueItem(BaseModel):
    reference: str
    case_type: str
    title: str
    severity: str
    status: str
    owner_role: str
    entity_name: str | None
    details: str


class RoleWorkspaceOut(BaseModel):
    role: str
    open_items: int
    critical_items: int
    high_items: int
    queue: list[RoleWorkQueueItem]
    recommended_panels: list[str]
    warnings: list[str]


class ProductionReadinessRow(BaseModel):
    control_code: str
    category: str
    status: str
    required: bool
    owner: str
    evidence: str


class ProductionReadinessOut(BaseModel):
    release: str
    overall_status: str
    readiness_pct: Decimal
    required_controls: int
    passed_controls: int
    blocked_controls: int
    rows: list[ProductionReadinessRow]
    deployment_authority: str
    warnings: list[str]

# MVP-21: Predictive Treasury Risk Radar
class TreasuryRiskRegimeFactor(BaseModel):
    factor_key: str
    recent_volatility: Decimal
    prior_volatility: Decimal
    volatility_ratio: Decimal
    regime: str


class TreasuryRiskRadarScenario(BaseModel):
    scenario_code: str
    description: str
    receivable_multiplier: Decimal
    payable_multiplier: Decimal
    facility_availability: Decimal
    fx_shock_pct: Decimal
    rate_shock_bps: int
    stressed_headroom: Decimal
    first_buffer_breach_week: int | None
    status: str


class TreasuryRiskRadarOut(BaseModel):
    reporting_currency: str
    horizon_days: int
    overall_status: str
    deterioration_score: Decimal
    liquidity_breach_probability: Decimal
    survival_horizon_days: int
    market_regime: str
    regime_confidence: Decimal
    top_lender_share: Decimal
    forecast_cash_bias_pct: Decimal
    regime_factors: list[TreasuryRiskRegimeFactor]
    dynamic_scenarios: list[TreasuryRiskRadarScenario]
    primary_drivers: list[str]
    execution_authority: str
    warnings: list[str]


# MVP-22: Strategic Treasury Optimization
class LiquidityBufferComponent(BaseModel):
    component: str
    amount_reporting: Decimal
    treatment: str
    rationale: str


class OptimalLiquidityBufferOut(BaseModel):
    reporting_currency: str
    current_minimum_cash: Decimal
    lower_buffer_bound: Decimal
    recommended_buffer: Decimal
    upper_buffer_bound: Decimal
    current_deployable_cash: Decimal
    buffer_surplus_or_gap: Decimal
    components: list[LiquidityBufferComponent]
    methodology: str
    execution_authority: str
    warnings: list[str]


class StrategicTreasuryRequest(BaseModel):
    horizon_years: int = 3
    objective: str = "BALANCED"
    incremental_funding_need: Decimal | None = None


class StrategicTreasuryOption(BaseModel):
    strategy_code: str
    description: str
    target_fixed_rate_share: Decimal
    target_fx_hedge_ratio: Decimal
    target_top_lender_share: Decimal
    target_long_term_funding_share: Decimal
    liquidity_buffer_target: Decimal
    incremental_hedge_reporting: Decimal
    modeled_tail_funding_need: Decimal
    residual_unfunded_tail: Decimal
    rate_cash_sensitivity_100bps: Decimal
    funding_concentration_status: str
    resilience_score: Decimal
    cost_data_completeness: str
    status: str


class StrategicTreasuryPlanOut(BaseModel):
    reporting_currency: str
    horizon_years: int
    objective: str
    selected_strategy_code: str
    current_fixed_rate_share: Decimal
    current_top_lender_share: Decimal
    optimal_liquidity_buffer: OptimalLiquidityBufferOut
    strategies: list[StrategicTreasuryOption]
    strategic_actions: list[str]
    human_approval_required: bool
    execution_authority: str
    warnings: list[str]

# Production Phase 1: real-data integration contracts
class ExternalMappingRow(BaseModel):
    connector_code: str
    object_type: str
    external_id: str
    internal_id: int | None = None
    internal_code: str | None = None
    active: bool


class ExternalMappingCreate(BaseModel):
    connector_code: str
    object_type: str
    external_id: str
    internal_id: int | None = None
    internal_code: str | None = None


class CanonicalBankBalanceIn(BaseModel):
    external_account_id: str
    currency: str
    book_balance: Decimal
    available_balance: Decimal | None = None
    restricted_balance: Decimal | None = None
    as_of: datetime
    source_record_id: str


class CanonicalERPFlowIn(BaseModel):
    external_reference: str
    legal_entity_code: str
    flow_type: str
    counterparty: str
    currency: str
    amount: Decimal
    due_date: date
    probability: Decimal = Decimal("1")
    status: str = "OPEN"
    source_timestamp: datetime | None = None


class CanonicalMarketQuoteIn(BaseModel):
    instrument: str
    asset_class: str
    base_currency: str | None = None
    quote_currency: str | None = None
    bid: Decimal | None = None
    ask: Decimal | None = None
    mid: Decimal
    as_of: datetime
    source: str
    source_record_id: str


class CanonicalBankBatchIn(BaseModel):
    connector_code: str
    source_system: str
    schema_version: str = "1.0"
    watermark: str | None = None
    balances: list[CanonicalBankBalanceIn]


class CanonicalERPBatchIn(BaseModel):
    connector_code: str
    source_system: str
    schema_version: str = "1.0"
    watermark: str | None = None
    flows: list[CanonicalERPFlowIn]


class CanonicalMarketBatchIn(BaseModel):
    connector_code: str
    source_system: str
    schema_version: str = "1.0"
    watermark: str | None = None
    quotes: list[CanonicalMarketQuoteIn]


class ISO20022BankStatementIn(BaseModel):
    connector_code: str
    source_system: str = "SWIFT_ISO20022"
    xml_payload: str
    schema_version: str = "ISO20022"


class IntegrationRunOut(BaseModel):
    id: int
    connector_code: str
    run_type: str
    status: str
    started_at: datetime
    completed_at: datetime | None
    records_received: int
    records_applied: int
    records_quarantined: int
    source_total: Decimal
    target_total: Decimal
    difference: Decimal
    watermark: str | None
    payload_hash: str | None
    error_detail: str


class DataLineageOut(BaseModel):
    id: int
    connector_code: str
    source_system: str
    source_object_type: str
    source_record_id: str
    target_table: str
    target_record_id: int | None
    source_timestamp: datetime | None
    ingested_at: datetime
    payload_hash: str
    schema_version: str
    reconciliation_status: str


class QuarantineOut(BaseModel):
    id: int
    connector_code: str
    record_type: str
    source_reference: str
    reason_code: str
    reason_detail: str
    quarantined_at: datetime
    resolved: bool
    resolution: str
    resolved_by: str | None = None
    resolved_at: datetime | None = None


class IntegrationIngestionOut(BaseModel):
    run_id: int
    connector_code: str
    status: str
    received: int
    applied: int
    quarantined: int
    source_total: Decimal
    target_total: Decimal
    difference: Decimal
    warnings: list[str]


class ISO20022ParseOut(BaseModel):
    message_type: str
    account_count: int
    balances: list[CanonicalBankBalanceIn]
    warnings: list[str]


class IntegrationCertificationRow(BaseModel):
    connector_code: str
    control_code: str
    required: bool
    status: str
    evidence: str
    owner: str
    last_checked_at: datetime | None


class ProductionPhase1StatusOut(BaseModel):
    phase: str
    overall_status: str
    integration_mode: str
    live_connector_count: int
    certified_connector_count: int
    recent_successful_runs: int
    recent_failed_runs: int
    open_quarantine_records: int
    stale_lineage_records: int
    certification: list[IntegrationCertificationRow]
    warnings: list[str]

class CanonicalBankTransactionIn(BaseModel):
    external_account_id: str
    source_record_id: str
    booking_date: date
    value_date: date | None = None
    currency: str
    amount: Decimal
    credit_debit: str
    counterparty: str = ""
    reference: str = ""
    status: str = "BOOKED"


class CanonicalBankTransactionBatchIn(BaseModel):
    connector_code: str
    source_system: str
    schema_version: str = "1.0"
    watermark: str | None = None
    transactions: list[CanonicalBankTransactionIn]


class CanonicalERPJournalIn(BaseModel):
    source_record_id: str
    legal_entity_code: str
    posting_date: date
    currency: str
    amount: Decimal
    counterparty: str = ""
    reference: str = ""
    document_type: str = "BANK_GL"


class CanonicalERPJournalBatchIn(BaseModel):
    connector_code: str
    source_system: str
    schema_version: str = "1.0"
    watermark: str | None = None
    journals: list[CanonicalERPJournalIn]


class CanonicalCurvePointIn(BaseModel):
    source_record_id: str
    curve_name: str
    currency: str
    curve_type: str = "DISCOUNT"
    tenor_days: int
    zero_rate: Decimal
    as_of: datetime
    source: str


class CanonicalVolatilityQuoteIn(BaseModel):
    source_record_id: str
    asset_class: str = "FX"
    underlying: str
    tenor_days: int
    quote_type: str = "ATM"
    volatility: Decimal
    as_of: datetime
    source: str


class CanonicalMarketRiskBatchIn(BaseModel):
    connector_code: str
    source_system: str
    schema_version: str = "1.0"
    watermark: str | None = None
    curve_points: list[CanonicalCurvePointIn] = []
    volatility_quotes: list[CanonicalVolatilityQuoteIn] = []


class ReconciliationExceptionOut(BaseModel):
    id: int
    reconciliation_run_id: int
    bank_transaction_id: int | None
    erp_journal_id: int | None
    exception_type: str
    amount_difference: Decimal
    detail: str
    status: str


class DetailedReconciliationOut(BaseModel):
    run_id: int
    status: str
    bank_transaction_count: int
    erp_journal_count: int
    matched_count: int
    unmatched_bank_count: int
    unmatched_erp_count: int
    source_total: Decimal
    target_total: Decimal
    difference: Decimal
    exceptions: list[ReconciliationExceptionOut]
    warnings: list[str]

class ISO20022IngestionOut(BaseModel):
    message_type: str
    balance_result: IntegrationIngestionOut
    transaction_result: IntegrationIngestionOut
    warnings: list[str]


class ReconciliationRequest(BaseModel):
    bank_connector_code: str
    erp_connector_code: str
    start_date: date
    end_date: date
    amount_tolerance: Decimal = Decimal("0.01")
    date_tolerance_days: int = 2

class IntegrationCertificationUpdate(BaseModel):
    status: str
    evidence: str


class RealDataCoverageOut(BaseModel):
    reporting_currency: str
    overall_status: str
    bank_account_coverage_pct: Decimal
    erp_cashflow_coverage_pct: Decimal
    market_currency_coverage_pct: Decimal
    reconciliation_pass_rate: Decimal
    bank_accounts_total: int
    bank_accounts_real_data: int
    open_cashflows_total: int
    open_cashflows_real_data: int
    required_market_currencies: int
    fresh_market_currencies: int
    reconciliation_runs: int
    reconciliation_passes: int
    blockers: list[str]
    warnings: list[str]


# Production Phase 1 v2: shadow promotion and parallel-run validation
class SourceAuthorityUpdate(BaseModel):
    mode: str
    evidence: str = ""


class SourceAuthorityOut(BaseModel):
    connector_code: str
    data_domain: str
    mode: str
    evidence: str
    approved_by: str | None
    approved_at: datetime | None
    updated_at: datetime


class ShadowRecordOut(BaseModel):
    id: int
    connector_code: str
    data_domain: str
    source_record_id: str
    mapped_internal_id: int | None
    target_table: str
    currency: str | None
    amount: Decimal | None
    as_of: datetime | None
    payload_hash: str
    status: str
    ingested_at: datetime


class DataQualitySLAOut(BaseModel):
    connector_code: str
    data_domain: str
    as_of: datetime
    timeliness_score: Decimal
    completeness_score: Decimal
    validity_score: Decimal
    uniqueness_score: Decimal
    reconciliation_score: Decimal
    overall_score: Decimal
    status: str
    breaches: list[str]


class ParallelRunObservationIn(BaseModel):
    connector_code: str
    data_domain: str
    observation_date: date
    metric_name: str
    incumbent_value: Decimal
    platform_value: Decimal
    tolerance_pct: Decimal = Decimal("0.005")
    evidence: str = ""


class ParallelRunObservationOut(BaseModel):
    id: int
    connector_code: str
    data_domain: str
    observation_date: date
    metric_name: str
    incumbent_value: Decimal
    platform_value: Decimal
    absolute_difference: Decimal
    percentage_difference: Decimal
    tolerance_pct: Decimal
    status: str
    evidence: str


class ParallelRunSummaryOut(BaseModel):
    connector_code: str | None
    data_domain: str | None
    window_days: int
    observation_count: int
    distinct_observation_days: int
    pass_count: int
    pass_rate: Decimal
    maximum_percentage_difference: Decimal
    status: str
    blockers: list[str]
    warnings: list[str]


class QuarantineResolutionIn(BaseModel):
    resolution: str


class ParallelReadinessOut(BaseModel):
    status: str
    active_authority_count: int
    shadow_authority_count: int
    blocked_authority_count: int
    data_quality_pass_count: int
    parallel_run_status: str
    real_data_coverage_status: str
    blockers: list[str]
    warnings: list[str]
