export const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export type EntityLiquidity = {
  entity_id: number;
  entity_name: string;
  local_currency: string;
  liquidity_headroom_reporting: string;
  deployable_cash_reporting: string;
  undrawn_credit_reporting: string;
};

export type GlobalLiquidity = {
  reporting_currency: string;
  gross_cash: string;
  restricted_cash: string;
  committed_outflows: string;
  deployable_cash: string;
  minimum_cash: string;
  undrawn_credit: string;
  liquidity_headroom: string;
  entities: EntityLiquidity[];
  warnings: string[];
};

export type ForecastPoint = {
  week: number;
  week_start: string;
  week_end: string;
  expected_inflows: string;
  expected_outflows: string;
  closing_cash: string;
  available_facility: string;
  minimum_buffer: string;
  liquidity_headroom: string;
  shortfall: string;
};

export type LiquidityForecast = {
  scenario: string;
  scenario_label: string;
  reporting_currency: string;
  ending_cash: string;
  ending_liquidity_headroom: string;
  first_buffer_breach_week: number | null;
  maximum_shortfall: string;
  points: ForecastPoint[];
};

export type StressScenario = {
  scenario: string;
  scenario_label: string;
  ending_cash: string;
  minimum_headroom: string;
  maximum_shortfall: string;
  first_buffer_breach_week: number | null;
};

export type Finding = {
  agent: string;
  severity: string;
  title: string;
  message: string;
  metric?: string | null;
};

export type TreasurySummary = {
  ai_model: string;
  overall_status: string;
  findings: Finding[];
};

export type DerivativeRisk = {
  reporting_currency: string;
  open_trade_count: number;
  total_notional_reporting: string;
  net_market_value_reporting: string;
  positive_market_value_reporting: string;
  negative_market_value_reporting: string;
  unmapped_trade_count: number;
  maturity_buckets: Array<{
    bucket: string;
    notional_reporting: string;
    market_value_reporting_ccy: string;
    trade_count: number;
  }>;
  warnings: string[];
};

export type HedgeCoverage = {
  currency: string;
  underlying_exposure: string;
  hedge_notional: string;
  hedge_ratio: string | null;
  residual_exposure: string;
  policy_min: string;
  policy_max: string;
  status: string;
};

export type InterestRateRisk = {
  reporting_currency: string;
  total_debt: string;
  fixed_rate_debt: string;
  floating_rate_debt: string;
  pay_fixed_swap_notional: string;
  residual_floating_exposure: string;
  floating_share_before_hedges: string;
  floating_share_after_hedges: string;
  annual_cash_impact_100bps: string;
  annual_cash_impact_200bps: string;
  warnings: string[];
};

export type CounterpartyExposure = {
  counterparty: string;
  credit_rating: string | null;
  current_positive_mtm: string;
  potential_future_exposure: string;
  credit_exposure: string;
  exposure_limit: string;
  utilization: string;
  status: string;
};

export type MarketStress = {
  reporting_currency: string;
  fx_shock_pct: string;
  rate_shock_bps: number;
  estimated_fx_adverse_change: string;
  annual_rate_cash_impact: string;
  near_term_derivative_negative_mtm: string;
  combined_market_liquidity_call: string;
  warnings: string[];
};

export type AgentRuntime = {
  model: string;
  llm_enabled: boolean;
  top_level_agents: string[];
  specialist_agents: string[];
  deterministic_engines: string[];
  controls: string[];
};

async function getJson<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, { cache: "no-store", ...init });
  if (!response.ok) throw new Error(`Unable to load ${path}`);
  return response.json();
}

export const getLiquidity = () => getJson<GlobalLiquidity>("/api/v1/liquidity/global");
export const getTreasurySummary = () => getJson<TreasurySummary>("/api/v1/agents/treasury-summary");
export const getForecast = (scenario = "BASE") => getJson<LiquidityForecast>(`/api/v1/liquidity/forecast?scenario=${scenario}&weeks=13`);
export const getStressSummary = () => getJson<StressScenario[]>("/api/v1/liquidity/stress?weeks=13");
export const getDerivativeRisk = () => getJson<DerivativeRisk>("/api/v1/risk/derivatives");
export const getHedgeCoverage = () => getJson<HedgeCoverage[]>("/api/v1/risk/hedging");
export const getInterestRateRisk = () => getJson<InterestRateRisk>("/api/v1/risk/interest-rates");
export const getCounterpartyRisk = () => getJson<CounterpartyExposure[]>("/api/v1/risk/counterparties");
export const getMarketStress = () => getJson<MarketStress>("/api/v1/risk/market-stress?fx_shock_pct=0.10&rate_shock_bps=100");
export const getAgentRuntime = () => getJson<AgentRuntime>("/api/v1/agents/runtime");

export type CashMobility = {
  reporting_currency: string;
  total_deployable_cash: string;
  total_trapped_cash: string;
  total_transferable_surplus: string;
  total_local_cash_deficit: string;
  entities: Array<{
    entity_id: number;
    entity_name: string;
    country_code: string;
    trapped_cash_reporting: string;
    transferable_surplus_reporting: string;
    local_cash_deficit_reporting: string;
    restriction_reasons: string[];
  }>;
  warnings: string[];
};

export type CashPool = {
  pool_name: string;
  pool_type: string;
  currency: string;
  header_entity: string;
  total_contribution_capacity: string;
  total_funding_need: string;
  internal_offset_capacity: string;
};

export type CrossBorderFunding = {
  facility_id: number;
  lender_entity: string;
  borrower_entity: string;
  currency: string;
  available_amount_reporting: string;
  interest_rate: string;
  transfer_pricing_status: string;
  withholding_tax_rate: string | null;
  estimated_annual_withholding_tax_reporting: string | null;
  tax_rule_status: string;
};

export type CollateralLiquidity = {
  reporting_currency: string;
  current_margin_call: string;
  stressed_margin_call: string;
  rows: Array<{
    counterparty: string;
    current_margin_call_reporting: string;
    stressed_margin_call_reporting: string;
    status: string;
  }>;
};

export type RefinancingRisk = {
  reporting_currency: string;
  debt_due_90d: string;
  debt_due_180d: string;
  debt_due_365d: string;
  committed_facilities_due_90d: string;
  liquidity_headroom: string;
  covenants: Array<{
    lender: string;
    covenant_code: string;
    metric_name: string;
    current_value: string;
    threshold_value: string;
    headroom_pct: string;
    status: string;
  }>;
};

export const getCashMobility = () => getJson<CashMobility>("/api/v1/liquidity/mobility");
export const getCashPools = () => getJson<CashPool[]>("/api/v1/liquidity/cash-pools");
export const getCrossBorderFunding = () => getJson<CrossBorderFunding[]>("/api/v1/funding/intercompany");
export const getCollateralLiquidity = () => getJson<CollateralLiquidity>("/api/v1/risk/collateral");
export const getRefinancingRisk = () => getJson<RefinancingRisk>("/api/v1/risk/refinancing");

export type MarketDataFeedStatus = {
  feed_name: string;
  asset_class: string;
  source_type: string;
  status: string;
  age_minutes: number;
  stale_after_minutes: number;
  stale: boolean;
  execution_usable: boolean;
};

export type ConnectorStatus = {
  connector_name: string;
  connector_type: string;
  system_name: string;
  status: string;
  age_minutes: number;
  stale_after_minutes: number;
  stale: boolean;
  execution_usable: boolean;
  owner: string;
};

export type ReconciliationStatus = {
  id: number;
  connector_name: string;
  run_type: string;
  difference: string;
  unmatched_count: number;
  status: string;
  run_at: string;
};

export type HedgeAccounting = {
  designation_id: number;
  derivative_position_id: number;
  instrument_type: string;
  counterparty: string;
  designation_type: string;
  hedged_item_reference: string;
  risk_component: string;
  hedge_ratio: string;
  documentation_status: string;
  effectiveness_status: string;
  accounting_standard: string;
  control_status: string;
};

export type TransactionProposal = {
  id: number;
  proposal_type: string;
  currency: string;
  amount: string;
  amount_reporting: string;
  purpose: string;
  created_by: string;
  status: string;
  control_status: string;
  required_approvals: number;
  approval_count: number;
};

export type ScenarioTemplate = {
  scenario_code: string;
  label: string;
  receivable_multiplier: string;
  payable_multiplier: string;
  facility_availability: string;
  fx_shock_pct: string;
  rate_shock_bps: number;
};

export type ReverseStress = {
  reporting_currency: string;
  weeks: number;
  trigger: string;
  receivable_multiplier: string;
  collection_haircut_pct: string;
  payable_multiplier: string;
  facility_availability: string;
  first_buffer_breach_week: number | null;
  maximum_shortfall: string;
  ending_liquidity_headroom: string;
  iterations: number;
};

export const getMarketDataControls = () => getJson<MarketDataFeedStatus[]>("/api/v1/controls/market-data");
export const getConnectorControls = () => getJson<ConnectorStatus[]>("/api/v1/controls/connectors");
export const getReconciliations = () => getJson<ReconciliationStatus[]>("/api/v1/controls/reconciliations");
export const getHedgeAccounting = () => getJson<HedgeAccounting[]>("/api/v1/accounting/hedges");
export const getTransactionProposals = () => getJson<TransactionProposal[]>("/api/v1/transactions/proposals");
export const getScenarioTemplates = () => getJson<ScenarioTemplate[]>("/api/v1/scenarios");
export const getReverseStress = () => getJson<ReverseStress>("/api/v1/risk/reverse-stress");

export type ModelValidation = {
  model_code: string; version: string; training_rows: number; validation_rows: number;
  mae_delay_days: string; brier_score: string; auc: string | null; validation_status: string;
};

export type ModelDrift = {
  model_code: string; delay_psi: string; late_rate_baseline: string; late_rate_recent: string;
  mean_delay_baseline: string; mean_delay_recent: string; status: string; notes: string[];
};

export type MLCashForecast = {
  reporting_currency: string; model_code: string; version: string; validation_status: string;
  first_conservative_breach_week: number | null; expected_ending_headroom: string;
  conservative_ending_headroom: string; optimistic_ending_headroom: string;
  points: Array<{week:number; expected_headroom:string; conservative_headroom:string; optimistic_headroom:string}>;
  payment_predictions: Array<{counterparty:string; due_date:string; late_probability:string; expected_delay_days:string; confidence:string}>;
  warnings: string[];
};

export type IntradayLiquidity = {
  reporting_currency: string; entity_name: string; opening_deployable_cash: string; minimum_buffer: string;
  available_committed_facility: string; lowest_projected_balance: string; peak_intraday_funding_need: string;
  first_buffer_breach_bucket: string | null;
  buckets: Array<{label:string; inflows:string; outflows:string; projected_balance:string; headroom:string}>;
  payment_priorities: Array<{payment_reference:string; counterparty:string; payment_type:string; amount_reporting:string; priority_score:number; recommended_action:string; anomaly_flag:boolean}>;
  warnings: string[];
};

export type PaymentAnomaly = { payment_reference:string; counterparty:string; payment_type:string; amount_reporting:string; anomaly_score:string; severity:string; reasons:string[] };
export type IPVSummary = { reporting_currency:string; pass_count:number; warning_count:number; fail_count:number; missing_count:number; rows:Array<{derivative_position_id:number; counterparty:string; book_mtm_reporting:string; independent_mid_reporting:string|null; absolute_deviation:string|null; status:string}>; warnings:string[] };
export type PaymentScreening = { payment_reference:string; counterparty:string; status:string; reason:string; execution_blocked:boolean };

export const getModelValidation = () => getJson<ModelValidation>("/api/v1/intelligence/model-validation");
export const getModelDrift = () => getJson<ModelDrift>("/api/v1/intelligence/model-drift");
export const getMLCashForecast = () => getJson<MLCashForecast>("/api/v1/intelligence/cash-forecast");
export const getIntradayLiquidity = () => getJson<IntradayLiquidity>("/api/v1/liquidity/intraday");
export const getPaymentAnomalies = () => getJson<PaymentAnomaly[]>("/api/v1/risk/payment-anomalies");
export const getIPV = () => getJson<IPVSummary>("/api/v1/controls/ipv");
export const getPaymentScreening = () => getJson<PaymentScreening[]>("/api/v1/controls/payment-screening");

export type InstitutionalValuation = {
  reporting_currency: string;
  total_model_value: string;
  total_book_value: string;
  aggregate_difference: string;
  priced_trade_count: number;
  unpriced_trade_count: number;
  rows: Array<{derivative_position_id:number; instrument_type:string; counterparty:string; model_type:string; model_value_reporting:string; book_value_reporting:string; valuation_difference:string; source_quality:string; model_status:string}>;
  warnings: string[];
};

export type LiquidityAtRisk = {
  reporting_currency: string;
  horizon_weeks: number;
  confidence: string;
  simulations: number;
  expected_ending_headroom: string;
  p05_ending_headroom: string;
  p01_ending_headroom: string;
  cash_flow_at_risk: string;
  liquidity_at_risk: string;
  probability_of_buffer_breach: string;
  expected_funding_need: string;
  tail_funding_need: string;
};

export type NettingSummary = {
  reporting_currency: string;
  gross_credit_exposure: string;
  net_credit_exposure: string;
  total_netting_benefit: string;
  legally_enforceable_sets: number;
  review_required_sets: number;
};

export type CollateralOptimization = {
  reporting_currency: string;
  total_additional_collateral_required: string;
  total_cross_currency_funding_required: string;
  rows: Array<{counterparty:string; netting_set_code:string; eligible_currency:string; additional_collateral_required:string; same_currency_available:string; cross_currency_funding_required:string; recommended_source_entity:string|null; status:string}>;
};

export type ChampionChallenger = {
  recommendation: string;
  auto_promotion_allowed: boolean;
  champion_mae: string;
  challenger_mae: string;
  mae_improvement_pct: string;
  brier_improvement_pct: string;
};

export type OperationalResilience = {
  overall_status: string;
  tier1_count: number;
  tier1_gaps: number;
  components: Array<{component_name:string; criticality_tier:string; rto_minutes:number; rpo_minutes:number; multi_region:boolean; last_dr_test_result:string; status:string}>;
};

export const getInstitutionalValuation = () => getJson<InstitutionalValuation>("/api/v1/valuation/institutional");
export const getLiquidityAtRisk = () => getJson<LiquidityAtRisk>("/api/v1/risk/liquidity-at-risk?simulations=2000");
export const getLegalNetting = () => getJson<NettingSummary>("/api/v1/risk/legal-netting");
export const getCollateralOptimization = () => getJson<CollateralOptimization>("/api/v1/risk/collateral-optimization");
export const getChampionChallenger = () => getJson<ChampionChallenger>("/api/v1/intelligence/champion-challenger");
export const getOperationalResilience = () => getJson<OperationalResilience>("/api/v1/ops/resilience");

export type LiveOperationsStatus = {
  status: string;
  events_24h: number;
  applied_24h: number;
  quarantined_24h: number;
  failed_24h: number;
  duplicate_events: number;
  max_event_lag_seconds: number;
  open_alerts: number;
  critical_alerts: number;
  last_event_received_at: string | null;
  checkpoints: Array<{
    connector_name: string;
    source_system: string;
    last_sequence_no: number | null;
    last_event_time: string | null;
    lag_seconds: number | null;
    accepted_count: number;
    duplicate_count: number;
    quarantined_count: number;
    failed_count: number;
    status: string;
  }>;
  warnings: string[];
};

export type LiveTreasuryAlert = {
  id: number;
  alert_key: string;
  category: string;
  severity: string;
  title: string;
  message: string;
  status: string;
  last_seen_at: string;
};

export type ExecutionMessage = {
  id: number;
  message_id: string;
  proposal_id: number;
  connector_name: string;
  status: string;
  created_at: string;
  sent_at: string | null;
  acknowledged_at: string | null;
  external_reference: string | null;
};

export const getLiveOperationsStatus = () => getJson<LiveOperationsStatus>("/api/v1/operations/live-status");
export const getLiveTreasuryAlerts = () => getJson<LiveTreasuryAlert[]>("/api/v1/operations/alerts");
export const getExecutionMessages = () => getJson<ExecutionMessage[]>("/api/v1/execution/messages");

export type HedgeOptimization = {
  reporting_currency: string;
  target_hedge_ratio: string;
  total_incremental_hedge_reporting: string;
  estimated_execution_liquidity_cost_reporting: string;
  rows: Array<{currency:string; action:string; status:string; target_hedge_ratio:string; incremental_hedge_notional:string; residual_exposure_after:string}>;
  assumptions: string[];
  warnings: string[];
};

export type FundingOptimization = {
  reporting_currency: string;
  requested_funding_need: string;
  covered_funding: string;
  uncovered_funding: string;
  internal_cash_mobilization_cap: string;
  rows: Array<{source_type:string; source_name:string; capacity_reporting:string; allocated_reporting:string; estimated_annual_cost_reporting:string|null; cost_rate:string|null; control_status:string; notes:string}>;
  warnings: string[];
};

export type ScenarioSearch = {
  reporting_currency: string;
  combinations_tested: number;
  breach_count: number;
  worst_stressed_headroom: string;
  rows: Array<{rank:number; receivable_multiplier:string; payable_multiplier:string; facility_availability:string; fx_shock_pct:string; rate_shock_bps:number; stressed_headroom:string; maximum_shortfall:string; first_buffer_breach_week:number|null; status:string}>;
  methodology: string;
  warnings: string[];
};

export type TreasuryDecisionPack = {
  reporting_currency: string;
  decision_objective: string;
  recommended_strategy_code: string;
  strategies: Array<{strategy_code:string; description:string; hedge_target_ratio:string; cash_mobilization_pct:string; contingency_prefunding_pct:string; tail_funding_target:string; projected_internal_cash_use:string; projected_external_capacity_use:string; residual_unfunded_tail:string; estimated_hedge_execution_cost:string; policy_exception_count:number; resilience_score:string; decision_status:string}>;
  scenario_search: ScenarioSearch;
  human_approval_required: boolean;
  execution_authority: string;
  decision_notes: string[];
};

export const getHedgeOptimization = () => getJson<HedgeOptimization>("/api/v1/optimization/hedges", { method: "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify({}) });
export const getFundingOptimization = () => getJson<FundingOptimization>("/api/v1/optimization/funding");
export const getScenarioSearch = () => getJson<ScenarioSearch>("/api/v1/optimization/scenario-search?top_n=5");
export const getTreasuryDecisionPack = () => getJson<TreasuryDecisionPack>("/api/v1/optimization/decision-pack?objective=BALANCED");

export type MarketRiskDistribution = {
  reporting_currency: string;
  horizon_days: number;
  confidence: string;
  simulations: number;
  portfolio_var_95: string;
  portfolio_expected_shortfall_95: string;
  earnings_at_risk_95_90d: string;
  rows: Array<{currency:string; residual_exposure_local:string; residual_exposure_reporting:string; annualized_volatility:string; var_95:string; expected_shortfall_95:string; data_status:string}>;
  methodology: string;
  warnings: string[];
};

export type LiquidityTransferPricing = {
  reporting_currency: string;
  benchmark_rate: string;
  surplus_credit_rate: string;
  deficit_charge_rate: string;
  net_internal_charge: string;
  rows: Array<{entity_id:number; entity_name:string; liquidity_position_reporting:string; position_type:string; internal_rate:string; annual_internal_charge_or_credit:string; status:string}>;
  methodology: string;
  warnings: string[];
};

export type BankAccountRationalization = {
  reporting_currency: string;
  account_count: number;
  bank_count: number;
  stale_account_count: number;
  review_candidate_count: number;
  largest_bank: string | null;
  largest_bank_share: string;
  rows: Array<{account_id:number; entity_name:string; bank_name:string; country_code:string; currency:string; deployable_balance_reporting:string; restricted_ratio:string; age_hours:number; role:string; recommendation:string; rationale:string}>;
  warnings: string[];
};

export type DigitalTwin = {
  twin_version: string;
  institutional_depth_version: string;
  reporting_currency: string;
  state: string;
  base_liquidity_headroom: string;
  scenario_stressed_headroom: string;
  first_buffer_breach_week: number | null;
  liquidity_at_risk_95: string;
  cash_flow_at_risk_95: string;
  buffer_breach_probability: string;
  market_var_95: string;
  market_expected_shortfall_95: string;
  intraday_peak_funding_need: string;
  trapped_cash: string;
  stressed_collateral_call: string;
  debt_due_180d: string;
  historical_market_var_95: string;
  xva_style_total: string;
  liquidity_survival_days: number;
  funding_top_lender_share: string;
  treasury_limit_status: string;
  actions: string[];
  assumptions: string[];
  warnings: string[];
};

export const getMarketRiskDistribution = () => getJson<MarketRiskDistribution>("/api/v1/risk/market-var?horizon_days=10&simulations=3000&seed=42");
export const getLiquidityTransferPricing = () => getJson<LiquidityTransferPricing>("/api/v1/liquidity/transfer-pricing");
export const getBankAccountRationalization = () => getJson<BankAccountRationalization>("/api/v1/operations/bank-account-rationalization");
export const getDigitalTwin = () => getJson<DigitalTwin>("/api/v1/digital-twin");

export type HistoricalMarketCalibration = {
  lookback_observations: number; ewma_lambda: string; source_status: string;
  factors: Array<{factor_key:string; observations:number; annualized_volatility:string; ewma_volatility:string; latest_return:string; data_status:string}>;
  correlations: Array<{factor_a:string; factor_b:string; correlation:string}>; warnings:string[];
};
export type HistoricalMarketRisk = { reporting_currency:string; horizon_days:number; confidence:string; portfolio_var:string; expected_shortfall:string; earnings_at_risk_90d:string; correlation_method:string; factor_count:number; warnings:string[] };
export type XVA = { reporting_currency:string; cva_style_total:string; fva_style_total:string; total_xva_style_adjustment:string; rows:Array<{counterparty:string; netting_set_code:string; total_xva_style_adjustment:string; data_status:string}>; warnings:string[] };
export type LiquiditySurvival = { reporting_currency:string; horizon_weeks:number; survival_horizon_days:number; first_buffer_breach_week:number|null; hard_liquidity_depletion_week:number|null; ending_effective_liquidity:string; minimum_effective_liquidity:string; status:string; warnings:string[] };
export type FundingConcentration = { reporting_currency:string; total_funding_reporting:string; lender_count:number; top_lender:string|null; top_lender_share:string; top_three_share:string; hhi:string; funding_due_180d:string; warnings:string[] };
export type RiskLimits = { overall_status:string; breach_count:number; warning_count:number; rows:Array<{limit_code:string; category:string; metric_name:string; comparator:string; threshold_value:string; current_value:string; utilization:string|null; status:string; owner:string}>; warnings:string[] };
export type TwinOptimization = { reporting_currency:string; objective:string; combinations_tested:number; selected_scenario_rank:number; execution_authority:string; scenarios:Array<{rank:number; stressed_headroom:string; survival_horizon_days:number; resilience_score:string; limit_breach_count:number; status:string}>; warnings:string[] };

export const getHistoricalMarketCalibration = () => getJson<HistoricalMarketCalibration>("/api/v1/risk/historical-calibration");
export const getHistoricalMarketRisk = () => getJson<HistoricalMarketRisk>("/api/v1/risk/historical-market-var");
export const getXVA = () => getJson<XVA>("/api/v1/risk/xva");
export const getLiquiditySurvival = () => getJson<LiquiditySurvival>("/api/v1/liquidity/survival-horizon");
export const getFundingConcentration = () => getJson<FundingConcentration>("/api/v1/funding/concentration");
export const getRiskLimits = () => getJson<RiskLimits>("/api/v1/risk/limits");
export const getTwinOptimization = () => getJson<TwinOptimization>("/api/v1/digital-twin/optimize", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({objective:"LIQUIDITY_RESILIENCE", weeks:13})});

// MVP-12: Enterprise liquidity command & predictive balance-sheet intelligence
export type StructuralLiquidityGap = {
  reporting_currency: string;
  opening_deployable_cash: string;
  minimum_cash_buffer: string;
  minimum_cumulative_cash_before_facilities: string;
  rows: Array<{bucket:string; start_day:number; end_day:number|null; probability_weighted_inflows:string; contractual_payables:string; debt_maturities:string; net_contractual_gap:string; cumulative_cash_before_facilities:string; committed_facility_capacity_expiring:string}>;
  warnings: string[];
};

export type RateGapDV01 = {
  reporting_currency: string;
  fixed_debt_reporting: string;
  floating_debt_reporting: string;
  residual_floating_reporting: string;
  annual_cash_impact_100bps: string;
  debt_dv01_proxy_reporting: string;
  swap_dv01_proxy_reporting: string;
  combined_dv01_proxy_reporting: string;
  warnings: string[];
};

export type FundingTenorOptimization = {
  reporting_currency:string; objective:string; requested_new_funding:string; current_funding_due_180d:string; current_top_lender_share:string; current_debt_due_180d:string;
  rows:Array<{tenor_bucket:string; target_share:string; proposed_amount_reporting:string}>;
  rationale:string; execution_authority:string; warnings:string[];
};

export type ContingencyFundingPlan = {
  reporting_currency:string; status:string; reference_tail_funding_need:string; survival_horizon_days:number; transferable_cash_capacity:string; committed_facility_capacity:string; uncovered_contingency_need:string;
  actions:Array<{stage:number; action:string; available_capacity_reporting:string; modeled_use_reporting:string; control_requirements:string}>;
  activation_triggers:string[]; execution_authority:string; warnings:string[];
};

export type TreasuryEarlyWarning = {
  overall_status:string; red_count:number; amber_count:number; green_count:number; governed_limit_status:string;
  indicators:Array<{indicator_code:string; current_value:string; amber_threshold:string; red_threshold:string; direction:string; unit:string; status:string}>;
  warnings:string[];
};

export type BalanceSheetTwin = {
  version:string; reporting_currency:string; scenario_label:string; status:string; stressed_liquidity_headroom:string; structural_cash_floor_before_facilities:string; survival_horizon_days:number; first_buffer_breach_week:number|null;
  residual_floating_rate_exposure:string; incremental_rate_cash_impact:string; fx_economic_value_sensitivity:string; collateral_or_derivative_liquidity_call:string; base_digital_twin_state:string; execution_authority:string; actions:string[]; warnings:string[];
};

export const getStructuralLiquidityGap = () => getJson<StructuralLiquidityGap>("/api/v1/liquidity/structural-gap");
export const getRateGapDV01 = () => getJson<RateGapDV01>("/api/v1/risk/rate-gap-dv01");
export const getFundingTenorOptimization = () => getJson<FundingTenorOptimization>("/api/v1/optimization/funding-tenor");
export const getContingencyFundingPlan = () => getJson<ContingencyFundingPlan>("/api/v1/liquidity/contingency-funding-plan");
export const getTreasuryEarlyWarning = () => getJson<TreasuryEarlyWarning>("/api/v1/risk/early-warning");
export const getBalanceSheetTwin = () => getJson<BalanceSheetTwin>("/api/v1/digital-twin/balance-sheet");

// MVP-13: Deep liquidity-risk intelligence
export type LiquidityConcentration = {
  reporting_currency:string; deployable_cash:string; transferable_surplus:string; trapped_cash:string; trapped_cash_share:string; transferability_ratio:string;
  rows:Array<{dimension:string; top_name:string|null; top_share:string; hhi:string; total_reporting:string; component_count:number}>;
  warnings:string[];
};
export type ProbabilisticLiquidity = {
  reporting_currency:string; horizon_weeks:number; simulations:number; seed:number; probability_of_any_buffer_breach:string; expected_first_breach_week_if_breached:string|null;
  p05_minimum_headroom:string; median_minimum_headroom:string; p95_minimum_headroom:string; tail_funding_need_95:string; expected_funding_need:string;
  weekly_distribution:Array<{week:number; p05_headroom:string; median_headroom:string; p95_headroom:string; breach_probability:string}>; methodology:string; warnings:string[];
};
export type ForecastDrivers = {
  reporting_currency:string; horizon_weeks:number; total_probability_weighted_inflows:string; total_contractual_outflows:string; absolute_projected_flow_base:string; largest_driver_share:string; top_five_driver_share:string;
  rows:Array<{counterparty:string; flow_type:string; currency:string; probability_weighted_reporting:string; signed_liquidity_impact:string; share_of_absolute_projected_flows:string}>; warnings:string[];
};
export type LiquidityActionPlaybook = {
  reporting_currency:string; trigger_status:string; reference_tail_funding_need:string; quantified_capacity_total:string; residual_uncovered_need:string;
  actions:Array<{priority:number; action:string; category:string; quantified_capacity_reporting:string|null; lead_time:string; prerequisites:string; execution_authority:string}>; warnings:string[];
};

export const getLiquidityConcentration = () => getJson<LiquidityConcentration>("/api/v1/liquidity/concentration");
export const getProbabilisticLiquidity = () => getJson<ProbabilisticLiquidity>("/api/v1/liquidity/probabilistic-path?simulations=1000&seed=42");
export const getForecastDrivers = () => getJson<ForecastDrivers>("/api/v1/liquidity/forecast-drivers?horizon_weeks=13&top_n=8");
export const getLiquidityActionPlaybook = () => getJson<LiquidityActionPlaybook>("/api/v1/liquidity/action-playbook");

// MVP-14: Forecast accuracy and working-capital liquidity intelligence
export type ForecastAccuracy = {
  reporting_currency:string; lookback_days:number; observation_count:number; overall_wape:string; cash_bias_pct:string; status:string;
  rows:Array<{segment_type:string; segment_value:string; observation_count:number; forecast_reporting:string; actual_reporting:string; absolute_error_reporting:string; wape:string; cash_bias_pct:string}>;
  warnings:string[];
};
export type ForecastBias = {
  reporting_currency:string; lookback_days:number; optimistic_bias_entities:number; conservative_bias_entities:number;
  rows:Array<{entity_name:string; inflow_bias_pct:string; outflow_bias_pct:string; cash_bias_pct:string; observation_count:number; status:string}>; warnings:string[];
};
export type WorkingCapitalCycle = {
  reporting_currency:string; latest_period_end:string; group_dso_days:string; group_dpo_days:string; group_dio_days:string; group_ccc_days:string; prior_group_ccc_days:string|null; group_ccc_change_days:string|null;
  rows:Array<{entity_name:string; period_end:string; revenue_reporting:string; cogs_reporting:string; dso_days:string; dpo_days:string; dio_days:string; ccc_days:string; prior_ccc_days:string|null; ccc_change_days:string|null}>; warnings:string[];
};
export type ReceivablesAging = {
  reporting_currency:string; total_open_receivables:string; total_overdue_receivables:string; overdue_share:string; probability_weighted_open_receivables:string;
  buckets:Array<{bucket:string; amount_reporting:string; probability_weighted_reporting:string; invoice_count:number}>;
  top_overdue_counterparties:Array<{counterparty:string; amount_reporting:string; days_overdue:number; collection_probability:string}>; warnings:string[];
};
export type WorkingCapitalLiquidityBridge = {
  reporting_currency:string; current_liquidity_headroom:string; dso_cash_release:string; dpo_cash_release:string; inventory_cash_release:string; total_modeled_cash_release:string; pro_forma_liquidity_headroom:string; execution_authority:string; warnings:string[];
};

export const getForecastAccuracy = () => getJson<ForecastAccuracy>("/api/v1/liquidity/forecast-accuracy?lookback_days=180");
export const getForecastBias = () => getJson<ForecastBias>("/api/v1/liquidity/forecast-bias?lookback_days=180");
export const getWorkingCapitalCycle = () => getJson<WorkingCapitalCycle>("/api/v1/working-capital/cycle");
export const getReceivablesAging = () => getJson<ReceivablesAging>("/api/v1/working-capital/receivables-aging");
export const getWorkingCapitalLiquidityBridge = () => getJson<WorkingCapitalLiquidityBridge>("/api/v1/working-capital/liquidity-bridge", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({dso_improvement_days:"5", dpo_extension_days:"3", dio_improvement_days:"5"})});

// MVP-15 to MVP-20: enterprise completion
export type CrossBorderGraph = { reporting_currency:string; active_route_count:number; executable_route_count:number; blocked_route_count:number; rows:Array<{source_country:string;target_country:string;transfer_type:string;currency:string|null;max_amount_reporting:string|null;withholding_tax_rate:string;regulatory_status:string;legal_status:string;executable:boolean;blockers:string[]}>; warnings:string[] };
export type LegalEntityLiquidityOptimization = { reporting_currency:string; transferable_surplus:string; local_deficit:string; proposed_transfer:string; unresolved_deficit:string; routes:Array<{source_entity:string;target_entity:string;source_country:string;target_country:string;transfer_type:string;currency:string;amount_reporting:string;estimated_withholding_cost:string;status:string;blockers:string[]}>; execution_authority:string; warnings:string[] };
export type ConnectorReadiness = { ready_count:number; degraded_count:number; blocked_count:number; rows:Array<{connector_code:string;connector_type:string;system_name:string;environment:string;status:string;readiness:string;gaps:string[]}>; canonical_contract_version:string; warnings:string[] };
export type EnterpriseSecurityPosture = { environment:string; overall_status:string; required_controls:number; passing_controls:number; failing_controls:number; coverage_pct:string; rows:Array<{control_code:string;domain:string;status:string;required:boolean;owner:string;evidence:string;age_days:number|null}>; warnings:string[] };
export type ProductionReadiness = { release:string; overall_status:string; readiness_pct:string; required_controls:number; passed_controls:number; blocked_controls:number; rows:Array<{control_code:string;category:string;status:string;required:boolean;owner:string;evidence:string}>; deployment_authority:string; warnings:string[] };
export type RoleWorkspace = { role:string; open_items:number; critical_items:number; high_items:number; queue:Array<{reference:string;case_type:string;title:string;severity:string;status:string;owner_role:string;entity_name:string|null;details:string}>; recommended_panels:string[]; warnings:string[] };

export const getCrossBorderGraph = () => getJson<CrossBorderGraph>("/api/v1/global-treasury/cross-border-constraints");
export const getLegalEntityLiquidityOptimization = () => getJson<LegalEntityLiquidityOptimization>("/api/v1/optimization/legal-entity-liquidity");
export const getEnterpriseConnectorReadiness = () => getJson<ConnectorReadiness>("/api/v1/integrations/readiness");
export const getEnterpriseSecurityPosture = () => getJson<EnterpriseSecurityPosture>("/api/v1/security/enterprise-posture");
export const getProductionReadiness = () => getJson<ProductionReadiness>("/api/v1/production/readiness");
export const getTreasurerWorkspace = () => getJson<RoleWorkspace>("/api/v1/workspaces/GROUP_TREASURER");

// MVP-21 / MVP-22: predictive risk radar and strategic treasury optimization
export type TreasuryRiskRadar = {
  reporting_currency:string; horizon_days:number; overall_status:string; deterioration_score:string;
  liquidity_breach_probability:string; survival_horizon_days:number; market_regime:string; regime_confidence:string;
  top_lender_share:string; forecast_cash_bias_pct:string;
  regime_factors:Array<{factor_key:string;recent_volatility:string;prior_volatility:string;volatility_ratio:string;regime:string}>;
  dynamic_scenarios:Array<{scenario_code:string;description:string;receivable_multiplier:string;payable_multiplier:string;facility_availability:string;fx_shock_pct:string;rate_shock_bps:number;stressed_headroom:string;first_buffer_breach_week:number|null;status:string}>;
  primary_drivers:string[]; execution_authority:string; warnings:string[];
};
export type OptimalLiquidityBuffer = {
  reporting_currency:string; current_minimum_cash:string; lower_buffer_bound:string; recommended_buffer:string; upper_buffer_bound:string;
  current_deployable_cash:string; buffer_surplus_or_gap:string;
  components:Array<{component:string;amount_reporting:string;treatment:string;rationale:string}>;
  methodology:string; execution_authority:string; warnings:string[];
};
export type StrategicTreasuryPlan = {
  reporting_currency:string; horizon_years:number; objective:string; selected_strategy_code:string; current_fixed_rate_share:string; current_top_lender_share:string;
  optimal_liquidity_buffer:OptimalLiquidityBuffer;
  strategies:Array<{strategy_code:string;description:string;target_fixed_rate_share:string;target_fx_hedge_ratio:string;target_top_lender_share:string;target_long_term_funding_share:string;liquidity_buffer_target:string;incremental_hedge_reporting:string;modeled_tail_funding_need:string;residual_unfunded_tail:string;rate_cash_sensitivity_100bps:string;funding_concentration_status:string;resilience_score:string;cost_data_completeness:string;status:string}>;
  strategic_actions:string[]; human_approval_required:boolean; execution_authority:string; warnings:string[];
};

export const getTreasuryRiskRadar = () => getJson<TreasuryRiskRadar>("/api/v1/intelligence/treasury-risk-radar?horizon_days=90");
export const getOptimalLiquidityBuffer = () => getJson<OptimalLiquidityBuffer>("/api/v1/strategy/optimal-liquidity-buffer");
export const getStrategicTreasuryPlan = () => getJson<StrategicTreasuryPlan>("/api/v1/strategy/treasury-plan", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({horizon_years:3, objective:"BALANCED"})});

// Production Phase 1: real-data integration status
export type ProductionPhase1Status = {
  phase:string;
  overall_status:string;
  integration_mode:string;
  live_connector_count:number;
  certified_connector_count:number;
  recent_successful_runs:number;
  recent_failed_runs:number;
  open_quarantine_records:number;
  stale_lineage_records:number;
  certification:Array<{connector_code:string;control_code:string;required:boolean;status:string;evidence:string;owner:string;last_checked_at:string|null}>;
  warnings:string[];
};

export const getProductionPhase1Status = () => getJson<ProductionPhase1Status>("/api/v1/integrations/phase1/status");

export type ProductionPhase1ParallelReadiness = {
  status:string;
  active_authority_count:number;
  shadow_authority_count:number;
  blocked_authority_count:number;
  data_quality_pass_count:number;
  parallel_run_status:string;
  real_data_coverage_status:string;
  blockers:string[];
  warnings:string[];
};

export type SourceAuthority = {
  connector_code:string;
  data_domain:string;
  mode:string;
  evidence:string;
  approved_by:string|null;
  approved_at:string|null;
  updated_at:string;
};

export const getProductionPhase1ParallelReadiness = () => getJson<ProductionPhase1ParallelReadiness>("/api/v1/integrations/phase1/parallel-readiness");
export const getSourceAuthorities = () => getJson<SourceAuthority[]>("/api/v1/integrations/phase1/authority");
