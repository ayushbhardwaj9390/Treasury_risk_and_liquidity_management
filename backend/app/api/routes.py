from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, Query, HTTPException, Header
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.orchestrator import TreasuryOrchestrator
from app.core.db import get_db
from app.core.security import treasury_identity, connector_identity
from app.models import LegalEntity, AuditLog
from app.schemas.treasury import (
    AgentRuntimeStatus,
    CounterpartyExposureRow,
    DerivativePositionOut,
    DerivativeRiskSummary,
    EntityOut,
    FXExposureRow,
    GlobalLiquidityOut,
    HedgeCoverageRow,
    InterestRateRiskOut,
    LiquidityForecastOut,
    MarketStressOut,
    MultiAgentAnalysisRequest,
    MultiAgentAnalysisResponse,
    MTMUpdateRequest,
    MTMUpdateResult,
    StressScenarioSummary,
    TreasuryCopilotRequest,
    TreasuryCopilotResponse,
    TreasurySummary,
    CashMobilityOut,
    CashPoolSummary,
    CrossBorderFundingOption,
    CollateralLiquidityOut,
    RefinancingRiskOut,
    UserAccessOut,
    MarketDataFeedStatus,
    ConnectorStatusOut,
    ReconciliationOut,
    HedgeAccountingOut,
    TransactionProposalCreate,
    TransactionProposalOut,
    ApprovalRequest,
    ExecutionRequest,
    ScenarioTemplateOut,
    ReverseStressOut,
    AuditEventOut,
    PaymentPredictionOut,
    ModelValidationOut,
    ModelDriftOut,
    ModelRegistryOut,
    MLCashForecastOut,
    IntradayLiquidityOut,
    PaymentAnomalyOut,
    IPVSummaryOut,
    MarketDataFallbackOut,
    PaymentScreeningOut,
    IntegratedScenarioRequest,
    IntegratedScenarioOut,
    InstitutionalValuationOut,
    LiquidityAtRiskOut,
    NettingSummaryOut,
    CollateralOptimizationOut,
    ChampionChallengerOut,
    OperationalResilienceOut,
    SecurityPostureOut,
    TreasuryEventIn,
    TreasuryEventOut,
    EventIngestionResult,
    EventReplayResult,
    LiveOperationsStatusOut,
    LiveMonitorRunOut,
    LiveTreasuryAlertOut,
    AlertAcknowledgementRequest,
    ExecutionMessageCreate,
    ExecutionMessageOut,
    ExecutionAcknowledgementRequest,
    HedgeOptimizationRequest,
    HedgeOptimizationOut,
    FundingOptimizationOut,
    CashPoolOptimizationOut,
    ScenarioSearchOut,
    TreasuryDecisionPackOut,
    MarketRiskDistributionOut,
    LiquidityTransferPricingOut,
    BankAccountRationalizationOut,
    DigitalTwinScenarioRequest,
    DigitalTwinOut,
    HistoricalMarketCalibrationOut,
    HistoricalMarketRiskOut,
    XVAOut,
    LiquiditySurvivalOut,
    FundingConcentrationOut,
    TreasuryRiskLimitFrameworkOut,
    DigitalTwinOptimizationRequest,
    DigitalTwinOptimizationOut,
    StructuralLiquidityGapOut,
    InterestRateGapDV01Out,
    FundingTenorOptimizationOut,
    CrossCurrencyFundingOut,
    ContingencyFundingPlanOut,
    EarlyWarningOut,
    BalanceSheetTwinRequest,
    BalanceSheetTwinOut,
    LiquidityConcentrationOut,
    ProbabilisticLiquidityOut,
    LiquidityAttributionRequest,
    LiquidityAttributionOut,
    ForecastDriverOut,
    LiquidityActionPlaybookOut,
    ForecastAccuracyOut,
    ForecastBiasOut,
    WorkingCapitalCycleOut,
    ReceivablesAgingOut,
    WorkingCapitalLiquidityBridgeRequest,
    WorkingCapitalLiquidityBridgeOut,
    CrossBorderConstraintGraphOut,
    LegalEntityLiquidityOptimizationOut,
    ConnectorReadinessOut,
    EnterpriseSecurityPostureOut,
    ModelValidationDashboardOut,
    RoleWorkspaceOut,
    ProductionReadinessOut,
    TreasuryRiskRadarOut,
    OptimalLiquidityBufferOut,
    StrategicTreasuryRequest,
    StrategicTreasuryPlanOut,
    ExternalMappingCreate,
    ExternalMappingRow,
    CanonicalBankBatchIn,
    CanonicalBankTransactionBatchIn,
    CanonicalERPBatchIn,
    CanonicalERPJournalBatchIn,
    CanonicalMarketBatchIn,
    CanonicalMarketRiskBatchIn,
    ISO20022BankStatementIn,
    ISO20022IngestionOut,
    IntegrationIngestionOut,
    IntegrationRunOut,
    DataLineageOut,
    QuarantineOut,
    ReconciliationRequest,
    DetailedReconciliationOut,
    ProductionPhase1StatusOut,
    IntegrationCertificationUpdate,
    IntegrationCertificationRow,
    RealDataCoverageOut,
    SourceAuthorityUpdate,
    SourceAuthorityOut,
    ShadowRecordOut,
    DataQualitySLAOut,
    ParallelRunObservationIn,
    ParallelRunObservationOut,
    ParallelRunSummaryOut,
    QuarantineResolutionIn,
    ParallelReadinessOut,
)
from app.services.derivative_risk import (
    calculate_counterparty_exposure,
    calculate_hedge_coverage,
    calculate_interest_rate_risk,
    derivative_risk_summary,
    list_derivatives,
    update_derivative_mtm,
)
from app.services.exposure import calculate_fx_exposures
from app.services.forecast import calculate_liquidity_forecast, calculate_stress_summary
from app.services.liquidity import calculate_global_liquidity
from app.services.market_stress import calculate_market_stress
from app.services.enterprise_controls import (
    list_user_access, market_data_health, connector_health, latest_reconciliations, hedge_accounting_status,
    create_transaction_proposal, list_transaction_proposals, approve_transaction_proposal, release_transaction_proposal,
)
from app.services.scenario_risk import list_scenario_templates, reverse_stress_collections
from app.services.advanced_intelligence import (
    predict_open_receivables, validate_payment_model, payment_model_drift, model_registry,
    calculate_ml_cash_forecast, calculate_intraday_liquidity, detect_payment_anomalies,
    independent_price_verification, select_market_data_fallback, payment_screening_status,
)
from app.services.integrated_scenario import calculate_integrated_scenario
from app.services.global_treasury import (
    calculate_cash_mobility,
    calculate_cash_pools,
    calculate_cross_border_funding,
    calculate_collateral_liquidity,
    calculate_refinancing_risk,
)
from app.services.institutional_risk import (
    calculate_institutional_valuation,
    calculate_liquidity_at_risk,
    calculate_legal_netting,
    optimize_collateral_liquidity,
    champion_challenger_analysis,
    operational_resilience_status,
    security_posture,
)
from app.services.live_operations import (
    ingest_treasury_event,
    replay_treasury_event,
    list_treasury_events,
    live_operations_status,
    run_live_monitor,
    list_live_alerts,
    acknowledge_live_alert,
    create_execution_message,
    list_execution_messages,
    mark_execution_message_sent,
    acknowledge_execution_message,
)

from app.services.digital_twin import (
    calculate_market_risk_distribution,
    calculate_liquidity_transfer_pricing,
    calculate_bank_account_rationalization,
    run_digital_twin,
)

from app.services.mvp11_risk import (
    calculate_historical_market_calibration,
    calculate_historical_market_risk,
    calculate_xva_style_adjustments,
    calculate_liquidity_survival_horizon,
    calculate_funding_concentration,
    evaluate_treasury_risk_limits,
    optimize_digital_twin_scenarios,
)

from app.services.treasury_optimization import (
    optimize_fx_hedges,
    optimize_funding,
    optimize_cash_pool,
    search_treasury_scenarios,
    build_treasury_decision_pack,
)

from app.services.mvp12_liquidity_command import (
    calculate_structural_liquidity_gap,
    calculate_interest_rate_gap_dv01,
    optimize_funding_tenor,
    analyze_cross_currency_funding,
    build_contingency_funding_plan,
    calculate_early_warning_indicators,
    run_balance_sheet_twin,
)
from app.services.mvp13_liquidity_intelligence import (
    calculate_liquidity_concentration,
    calculate_probabilistic_liquidity_path,
    calculate_liquidity_stress_attribution,
    calculate_forecast_driver_concentration,
    build_liquidity_action_playbook,
)
from app.services.mvp14_forecast_working_capital import (
    calculate_forecast_accuracy,
    calculate_forecast_bias,
    calculate_working_capital_cycle,
    calculate_receivables_aging,
    calculate_working_capital_liquidity_bridge,
)


from app.services.mvp21_22_predictive_strategy import (
    calculate_treasury_risk_radar,
    calculate_optimal_liquidity_buffer,
    optimize_strategic_treasury,
)


from app.services.production_phase1 import (
    create_external_mapping,
    list_external_mappings,
    ingest_bank_balances,
    ingest_bank_transactions,
    ingest_erp_flows,
    ingest_erp_journals,
    ingest_market_quotes,
    ingest_market_risk_data,
    ingest_iso20022_statement,
    run_bank_erp_reconciliation,
    list_integration_runs,
    list_lineage,
    list_quarantine,
    production_phase1_status,
    update_integration_certification,
    real_data_coverage,
    list_source_authorities,
    list_shadow_records,
    record_parallel_run_observation,
    parallel_run_summary,
    evaluate_data_quality_sla,
    update_source_authority,
    resolve_quarantine_record,
    parallel_readiness,
)

router = APIRouter(prefix="/api/v1")

from app.services.mvp15_20_enterprise import (
    cross_border_constraint_graph,
    optimize_legal_entity_liquidity,
    enterprise_connector_readiness,
    enterprise_security_posture,
    model_validation_dashboard,
    role_workspace,
    production_readiness,
)


@router.get("/entities", response_model=list[EntityOut])
def list_entities(db: Session = Depends(get_db)):
    return db.scalars(select(LegalEntity).order_by(LegalEntity.name)).all()


@router.get("/liquidity/global", response_model=GlobalLiquidityOut)
def global_liquidity(db: Session = Depends(get_db)):
    return calculate_global_liquidity(db)


@router.get("/exposures/fx", response_model=list[FXExposureRow])
def fx_exposure(db: Session = Depends(get_db)):
    return calculate_fx_exposures(db)


@router.get("/agents/runtime", response_model=AgentRuntimeStatus)
def agent_runtime():
    return TreasuryOrchestrator().runtime_status()


@router.get("/agents/treasury-summary", response_model=TreasurySummary)
def treasury_summary(db: Session = Depends(get_db)):
    return TreasuryOrchestrator().run(db)


@router.post("/agents/copilot", response_model=TreasuryCopilotResponse)
async def treasury_copilot(request: TreasuryCopilotRequest, db: Session = Depends(get_db)):
    return await TreasuryOrchestrator().answer(db, request.question, request.include_market_stress)


@router.post("/agents/analyze", response_model=MultiAgentAnalysisResponse)
async def multi_agent_analysis(request: MultiAgentAnalysisRequest, db: Session = Depends(get_db)):
    return await TreasuryOrchestrator().multi_agent_analysis(db, request.question, request.mode)


@router.get("/liquidity/forecast", response_model=LiquidityForecastOut)
def liquidity_forecast(
    scenario: Literal["BASE", "MODERATE", "SEVERE"] = "BASE",
    weeks: int = Query(13, ge=1, le=52),
    db: Session = Depends(get_db),
):
    return calculate_liquidity_forecast(db, scenario, weeks)


@router.get("/liquidity/stress", response_model=list[StressScenarioSummary])
def liquidity_stress(weeks: int = Query(13, ge=1, le=52), db: Session = Depends(get_db)):
    return calculate_stress_summary(db, weeks)


@router.get("/risk/market-stress", response_model=MarketStressOut)
def market_stress(
    fx_shock_pct: Decimal = Query(Decimal("0.10"), ge=Decimal("0"), le=Decimal("0.50")),
    rate_shock_bps: int = Query(100, ge=0, le=1000),
    db: Session = Depends(get_db),
):
    return calculate_market_stress(db, fx_shock_pct, rate_shock_bps)


@router.get("/derivatives", response_model=list[DerivativePositionOut])
def derivatives(db: Session = Depends(get_db)):
    return list_derivatives(db)


@router.post("/derivatives/mtm", response_model=MTMUpdateResult)
def update_mtm(request: MTMUpdateRequest, db: Session = Depends(get_db)):
    updated, audit_id = update_derivative_mtm(db, request.updates, request.actor)
    return MTMUpdateResult(updated_trade_ids=updated, audit_event_id=audit_id)


@router.get("/risk/derivatives", response_model=DerivativeRiskSummary)
def derivatives_risk(db: Session = Depends(get_db)):
    return derivative_risk_summary(db)


@router.get("/risk/hedging", response_model=list[HedgeCoverageRow])
def hedging_risk(db: Session = Depends(get_db)):
    return calculate_hedge_coverage(db)


@router.get("/risk/counterparties", response_model=list[CounterpartyExposureRow])
def counterparty_risk(db: Session = Depends(get_db)):
    return calculate_counterparty_exposure(db)


@router.get("/risk/interest-rates", response_model=InterestRateRiskOut)
def interest_rate_risk(db: Session = Depends(get_db)):
    return calculate_interest_rate_risk(db)


@router.get("/liquidity/mobility", response_model=CashMobilityOut)
def cash_mobility(db: Session = Depends(get_db)):
    return calculate_cash_mobility(db)


@router.get("/liquidity/cash-pools", response_model=list[CashPoolSummary])
def cash_pools(db: Session = Depends(get_db)):
    return calculate_cash_pools(db)


@router.get("/funding/intercompany", response_model=list[CrossBorderFundingOption])
def intercompany_funding(db: Session = Depends(get_db)):
    return calculate_cross_border_funding(db)


@router.get("/risk/collateral", response_model=CollateralLiquidityOut)
def collateral_liquidity(db: Session = Depends(get_db)):
    return calculate_collateral_liquidity(db)


@router.get("/risk/refinancing", response_model=RefinancingRiskOut)
def refinancing_risk(db: Session = Depends(get_db)):
    return calculate_refinancing_risk(db)


@router.get("/controls/users", response_model=list[UserAccessOut])
def access_users(db: Session = Depends(get_db)):
    return list_user_access(db)


@router.get("/controls/market-data", response_model=list[MarketDataFeedStatus])
def market_data_controls(db: Session = Depends(get_db)):
    return market_data_health(db)


@router.get("/controls/connectors", response_model=list[ConnectorStatusOut])
def connector_controls(db: Session = Depends(get_db)):
    return connector_health(db)


@router.get("/controls/reconciliations", response_model=list[ReconciliationOut])
def reconciliation_controls(db: Session = Depends(get_db)):
    return latest_reconciliations(db)


@router.get("/accounting/hedges", response_model=list[HedgeAccountingOut])
def hedge_accounting_controls(db: Session = Depends(get_db)):
    return hedge_accounting_status(db)


@router.get("/transactions/proposals", response_model=list[TransactionProposalOut])
def transaction_proposals(db: Session = Depends(get_db)):
    return list_transaction_proposals(db)


@router.post("/transactions/proposals", response_model=TransactionProposalOut)
def create_proposal(request: TransactionProposalCreate, x_treasury_user: str = Depends(treasury_identity), db: Session = Depends(get_db)):
    try:
        return create_transaction_proposal(db, request, x_treasury_user)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/transactions/proposals/{proposal_id}/approve", response_model=TransactionProposalOut)
def approve_proposal(proposal_id: int, request: ApprovalRequest, x_treasury_user: str = Depends(treasury_identity), db: Session = Depends(get_db)):
    try:
        return approve_transaction_proposal(db, proposal_id, x_treasury_user, request.decision, request.comment)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/transactions/proposals/{proposal_id}/release", response_model=TransactionProposalOut)
def release_proposal(proposal_id: int, request: ExecutionRequest, x_treasury_user: str = Depends(treasury_identity), db: Session = Depends(get_db)):
    try:
        return release_transaction_proposal(db, proposal_id, x_treasury_user)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/scenarios", response_model=list[ScenarioTemplateOut])
def scenario_library(db: Session = Depends(get_db)):
    return list_scenario_templates(db)


@router.get("/risk/reverse-stress", response_model=ReverseStressOut)
def reverse_stress(
    weeks: int = Query(13, ge=1, le=52),
    payable_multiplier: Decimal = Query(Decimal("1.10"), ge=Decimal("1"), le=Decimal("2")),
    facility_availability: Decimal = Query(Decimal("0.75"), ge=Decimal("0"), le=Decimal("1")),
    db: Session = Depends(get_db),
):
    return reverse_stress_collections(db, weeks, payable_multiplier, facility_availability)


@router.get("/controls/audit-events", response_model=list[AuditEventOut])
def audit_events(limit: int = Query(100, ge=1, le=500), db: Session = Depends(get_db)):
    rows = db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)).all()
    return [AuditEventOut(id=x.id, event_type=x.event_type, actor=x.actor, details=x.details, created_at=x.created_at) for x in rows]


@router.get("/intelligence/payment-predictions", response_model=list[PaymentPredictionOut])
def payment_predictions(db: Session = Depends(get_db)):
    return predict_open_receivables(db)


@router.get("/intelligence/model-validation", response_model=ModelValidationOut)
def model_validation(db: Session = Depends(get_db)):
    return validate_payment_model(db)


@router.get("/intelligence/model-drift", response_model=ModelDriftOut)
def model_drift(db: Session = Depends(get_db)):
    return payment_model_drift(db)


@router.get("/intelligence/model-registry", response_model=list[ModelRegistryOut])
def registry(db: Session = Depends(get_db)):
    return model_registry(db)


@router.get("/intelligence/cash-forecast", response_model=MLCashForecastOut)
def ml_cash_forecast(weeks: int = Query(13, ge=1, le=52), db: Session = Depends(get_db)):
    return calculate_ml_cash_forecast(db, weeks)


@router.get("/liquidity/intraday", response_model=IntradayLiquidityOut)
def intraday_liquidity(entity_id: int | None = Query(None), db: Session = Depends(get_db)):
    return calculate_intraday_liquidity(db, entity_id)


@router.get("/risk/payment-anomalies", response_model=list[PaymentAnomalyOut])
def payment_anomalies(entity_id: int | None = Query(None), db: Session = Depends(get_db)):
    return detect_payment_anomalies(db, entity_id)


@router.get("/controls/ipv", response_model=IPVSummaryOut)
def ipv_controls(db: Session = Depends(get_db)):
    return independent_price_verification(db)


@router.get("/controls/market-data/fallback", response_model=MarketDataFallbackOut)
def market_data_fallback(asset_class: str = Query("FX"), db: Session = Depends(get_db)):
    return select_market_data_fallback(db, asset_class.upper())


@router.get("/controls/payment-screening", response_model=list[PaymentScreeningOut])
def payment_screening(db: Session = Depends(get_db)):
    return payment_screening_status(db)


@router.post("/risk/integrated-scenario", response_model=IntegratedScenarioOut)
def integrated_scenario(request: IntegratedScenarioRequest, db: Session = Depends(get_db)):
    return calculate_integrated_scenario(db, request)


@router.get("/valuation/institutional", response_model=InstitutionalValuationOut)
def institutional_valuation(db: Session = Depends(get_db)):
    return calculate_institutional_valuation(db)


@router.get("/risk/liquidity-at-risk", response_model=LiquidityAtRiskOut)
def liquidity_at_risk(
    horizon_weeks: int = Query(13, ge=1, le=52),
    confidence: Decimal = Query(Decimal("0.95"), ge=Decimal("0.90"), lt=Decimal("1")),
    simulations: int = Query(4000, ge=500, le=20000),
    seed: int = Query(42, ge=0, le=1000000),
    db: Session = Depends(get_db),
):
    return calculate_liquidity_at_risk(db, horizon_weeks, confidence, simulations, seed)


@router.get("/risk/legal-netting", response_model=NettingSummaryOut)
def legal_netting(db: Session = Depends(get_db)):
    return calculate_legal_netting(db)


@router.get("/risk/collateral-optimization", response_model=CollateralOptimizationOut)
def collateral_optimization(db: Session = Depends(get_db)):
    return optimize_collateral_liquidity(db)


@router.get("/intelligence/champion-challenger", response_model=ChampionChallengerOut)
def champion_challenger(db: Session = Depends(get_db)):
    return champion_challenger_analysis(db)


@router.get("/ops/resilience", response_model=OperationalResilienceOut)
def resilience(db: Session = Depends(get_db)):
    return operational_resilience_status(db)


@router.get("/ops/security", response_model=SecurityPostureOut)
def security_status():
    return security_posture()


@router.post("/events/ingest", response_model=EventIngestionResult)
def ingest_event(request: TreasuryEventIn, x_connector_name: str = Depends(connector_identity), db: Session = Depends(get_db)):
    if request.connector_name != x_connector_name:
        raise HTTPException(status_code=403, detail="Connector identity does not match event connector_name")
    try:
        return ingest_treasury_event(db, request)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/events", response_model=list[TreasuryEventOut])
def treasury_events(limit: int = Query(100, ge=1, le=1000), db: Session = Depends(get_db)):
    return list_treasury_events(db, limit)


@router.post("/events/{event_id}/replay", response_model=EventReplayResult)
def replay_event(event_id: int, x_treasury_user: str = Depends(treasury_identity), db: Session = Depends(get_db)):
    try:
        return replay_treasury_event(db, event_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/operations/live-status", response_model=LiveOperationsStatusOut)
def live_status(db: Session = Depends(get_db)):
    return live_operations_status(db)


@router.post("/operations/monitor/run", response_model=LiveMonitorRunOut)
def run_monitor(x_treasury_user: str = Depends(treasury_identity), db: Session = Depends(get_db)):
    return run_live_monitor(db)


@router.get("/operations/alerts", response_model=list[LiveTreasuryAlertOut])
def live_alerts(status: str | None = Query(None), db: Session = Depends(get_db)):
    return list_live_alerts(db, status)


@router.post("/operations/alerts/{alert_id}/ack", response_model=LiveTreasuryAlertOut)
def acknowledge_alert(alert_id: int, request: AlertAcknowledgementRequest, x_treasury_user: str = Depends(treasury_identity), db: Session = Depends(get_db)):
    try:
        return acknowledge_live_alert(db, alert_id, x_treasury_user, request.comment)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/execution/messages", response_model=list[ExecutionMessageOut])
def execution_messages(status: str | None = Query(None), db: Session = Depends(get_db)):
    return list_execution_messages(db, status)


@router.post("/transactions/proposals/{proposal_id}/execution-message", response_model=ExecutionMessageOut)
def build_execution_message(
    proposal_id: int,
    request: ExecutionMessageCreate,
    x_treasury_user: str = Depends(treasury_identity),
    idempotency_key_header: str | None = Header(None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
):
    if idempotency_key_header and idempotency_key_header != request.idempotency_key:
        raise HTTPException(status_code=409, detail="Idempotency-Key header must match request idempotency_key")
    try:
        return create_execution_message(db, proposal_id, request.connector_name, request.idempotency_key, x_treasury_user)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/execution/messages/{message_id}/sent", response_model=ExecutionMessageOut)
def execution_message_sent(message_id: str, x_connector_name: str = Depends(connector_identity), db: Session = Depends(get_db)):
    try:
        return mark_execution_message_sent(db, message_id, x_connector_name)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/execution/messages/{message_id}/ack", response_model=ExecutionMessageOut)
def execution_message_ack(message_id: str, request: ExecutionAcknowledgementRequest, x_connector_name: str = Depends(connector_identity), db: Session = Depends(get_db)):
    try:
        return acknowledge_execution_message(db, message_id, x_connector_name, request.status, request.external_reference, request.detail)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/optimization/hedges", response_model=HedgeOptimizationOut)
def hedge_optimization(request: HedgeOptimizationRequest, db: Session = Depends(get_db)):
    return optimize_fx_hedges(db, request)


@router.get("/optimization/funding", response_model=FundingOptimizationOut)
def funding_optimization(
    funding_need: Decimal | None = Query(None, ge=Decimal("0")),
    max_cash_mobilization_pct: Decimal = Query(Decimal("0.50"), ge=Decimal("0"), le=Decimal("1")),
    db: Session = Depends(get_db),
):
    return optimize_funding(db, funding_need, max_cash_mobilization_pct)


@router.get("/optimization/cash-pool", response_model=CashPoolOptimizationOut)
def cash_pool_optimization(db: Session = Depends(get_db)):
    return optimize_cash_pool(db)


@router.get("/optimization/scenario-search", response_model=ScenarioSearchOut)
def scenario_search(top_n: int = Query(10, ge=1, le=25), db: Session = Depends(get_db)):
    return search_treasury_scenarios(db, top_n=top_n)


@router.get("/optimization/decision-pack", response_model=TreasuryDecisionPackOut)
def treasury_decision_pack(
    objective: Literal["LIQUIDITY_PRESERVATION", "BALANCED", "RISK_REDUCTION"] = "BALANCED",
    db: Session = Depends(get_db),
):
    return build_treasury_decision_pack(db, objective)


@router.get("/risk/market-var", response_model=MarketRiskDistributionOut)
def market_var(
    horizon_days: int = Query(10, ge=1, le=252),
    confidence: Decimal = Query(Decimal("0.95"), ge=Decimal("0.90"), lt=Decimal("1")),
    simulations: int = Query(5000, ge=1000, le=50000),
    seed: int = Query(42, ge=0, le=1000000),
    db: Session = Depends(get_db),
):
    return calculate_market_risk_distribution(db, horizon_days, confidence, simulations, seed)


@router.get("/liquidity/transfer-pricing", response_model=LiquidityTransferPricingOut)
def liquidity_transfer_pricing(db: Session = Depends(get_db)):
    return calculate_liquidity_transfer_pricing(db)


@router.get("/operations/bank-account-rationalization", response_model=BankAccountRationalizationOut)
def bank_account_rationalization(db: Session = Depends(get_db)):
    return calculate_bank_account_rationalization(db)


@router.get("/digital-twin", response_model=DigitalTwinOut)
def digital_twin(db: Session = Depends(get_db)):
    return run_digital_twin(db)


@router.post("/digital-twin/simulate", response_model=DigitalTwinOut)
def digital_twin_simulate(request: DigitalTwinScenarioRequest, db: Session = Depends(get_db)):
    return run_digital_twin(db, request)


@router.get("/risk/historical-calibration", response_model=HistoricalMarketCalibrationOut)
def historical_market_calibration(
    lookback_observations: int = Query(120, ge=40, le=750),
    ewma_lambda: Decimal = Query(Decimal("0.94"), ge=Decimal("0.80"), lt=Decimal("1")),
    db: Session = Depends(get_db),
):
    return calculate_historical_market_calibration(db, lookback_observations, ewma_lambda)


@router.get("/risk/historical-market-var", response_model=HistoricalMarketRiskOut)
def historical_market_var(
    horizon_days: int = Query(10, ge=1, le=252),
    confidence: Decimal = Query(Decimal("0.95"), ge=Decimal("0.90"), lt=Decimal("1")),
    lookback_observations: int = Query(120, ge=40, le=750),
    db: Session = Depends(get_db),
):
    return calculate_historical_market_risk(db, horizon_days, confidence, lookback_observations)


@router.get("/risk/xva", response_model=XVAOut)
def xva_style_adjustments(db: Session = Depends(get_db)):
    return calculate_xva_style_adjustments(db)


@router.get("/liquidity/survival-horizon", response_model=LiquiditySurvivalOut)
def liquidity_survival_horizon(
    weeks: int = Query(26, ge=1, le=52),
    receivable_multiplier: Decimal = Query(Decimal("0.60"), ge=Decimal("0"), le=Decimal("1.5")),
    payable_multiplier: Decimal = Query(Decimal("1.20"), ge=Decimal("0"), le=Decimal("2")),
    facility_availability: Decimal = Query(Decimal("0.50"), ge=Decimal("0"), le=Decimal("1")),
    db: Session = Depends(get_db),
):
    return calculate_liquidity_survival_horizon(db, weeks, receivable_multiplier, payable_multiplier, facility_availability)


@router.get("/funding/concentration", response_model=FundingConcentrationOut)
def funding_concentration(db: Session = Depends(get_db)):
    return calculate_funding_concentration(db)


@router.get("/risk/limits", response_model=TreasuryRiskLimitFrameworkOut)
def treasury_risk_limits(db: Session = Depends(get_db)):
    return evaluate_treasury_risk_limits(db)


@router.post("/digital-twin/optimize", response_model=DigitalTwinOptimizationOut)
def digital_twin_optimize(request: DigitalTwinOptimizationRequest, db: Session = Depends(get_db)):
    return optimize_digital_twin_scenarios(db, request)


@router.get("/liquidity/structural-gap", response_model=StructuralLiquidityGapOut)
def structural_liquidity_gap(db: Session = Depends(get_db)):
    return calculate_structural_liquidity_gap(db)


@router.get("/risk/rate-gap-dv01", response_model=InterestRateGapDV01Out)
def rate_gap_dv01(db: Session = Depends(get_db)):
    return calculate_interest_rate_gap_dv01(db)


@router.get("/optimization/funding-tenor", response_model=FundingTenorOptimizationOut)
def funding_tenor_optimization(
    funding_need: Decimal | None = Query(None, ge=Decimal("0")),
    db: Session = Depends(get_db),
):
    return optimize_funding_tenor(db, funding_need)


@router.get("/optimization/cross-currency-funding", response_model=CrossCurrencyFundingOut)
def cross_currency_funding_optimization(db: Session = Depends(get_db)):
    return analyze_cross_currency_funding(db)


@router.get("/liquidity/contingency-funding-plan", response_model=ContingencyFundingPlanOut)
def contingency_funding_plan(db: Session = Depends(get_db)):
    return build_contingency_funding_plan(db)


@router.get("/risk/early-warning", response_model=EarlyWarningOut)
def treasury_early_warning(db: Session = Depends(get_db)):
    return calculate_early_warning_indicators(db)


@router.get("/digital-twin/balance-sheet", response_model=BalanceSheetTwinOut)
def balance_sheet_twin(db: Session = Depends(get_db)):
    return run_balance_sheet_twin(db)


@router.post("/digital-twin/balance-sheet/simulate", response_model=BalanceSheetTwinOut)
def balance_sheet_twin_simulate(request: BalanceSheetTwinRequest, db: Session = Depends(get_db)):
    return run_balance_sheet_twin(db, request)

@router.get("/liquidity/concentration", response_model=LiquidityConcentrationOut)
def liquidity_concentration(db: Session = Depends(get_db)):
    return calculate_liquidity_concentration(db)


@router.get("/liquidity/probabilistic-path", response_model=ProbabilisticLiquidityOut)
def probabilistic_liquidity_path(
    horizon_weeks: int = Query(13, ge=1, le=52),
    simulations: int = Query(3000, ge=500, le=20000),
    seed: int = Query(42, ge=0, le=1000000),
    db: Session = Depends(get_db),
):
    return calculate_probabilistic_liquidity_path(db, horizon_weeks, simulations, seed)


@router.post("/liquidity/stress-attribution", response_model=LiquidityAttributionOut)
def liquidity_stress_attribution(request: LiquidityAttributionRequest, db: Session = Depends(get_db)):
    return calculate_liquidity_stress_attribution(db, request)


@router.get("/liquidity/forecast-drivers", response_model=ForecastDriverOut)
def forecast_driver_concentration(
    horizon_weeks: int = Query(13, ge=1, le=52),
    top_n: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    return calculate_forecast_driver_concentration(db, horizon_weeks, top_n)


@router.get("/liquidity/action-playbook", response_model=LiquidityActionPlaybookOut)
def liquidity_action_playbook(db: Session = Depends(get_db)):
    return build_liquidity_action_playbook(db)



# MVP-14 forecast accuracy and working-capital liquidity intelligence
@router.get("/liquidity/forecast-accuracy", response_model=ForecastAccuracyOut)
def forecast_accuracy(
    lookback_days: int = Query(180, ge=30, le=730),
    db: Session = Depends(get_db),
):
    return calculate_forecast_accuracy(db, lookback_days)


@router.get("/liquidity/forecast-bias", response_model=ForecastBiasOut)
def forecast_bias(
    lookback_days: int = Query(180, ge=30, le=730),
    db: Session = Depends(get_db),
):
    return calculate_forecast_bias(db, lookback_days)


@router.get("/working-capital/cycle", response_model=WorkingCapitalCycleOut)
def working_capital_cycle(db: Session = Depends(get_db)):
    return calculate_working_capital_cycle(db)


@router.get("/working-capital/receivables-aging", response_model=ReceivablesAgingOut)
def receivables_aging(db: Session = Depends(get_db)):
    return calculate_receivables_aging(db)


@router.post("/working-capital/liquidity-bridge", response_model=WorkingCapitalLiquidityBridgeOut)
def working_capital_liquidity_bridge(
    request: WorkingCapitalLiquidityBridgeRequest,
    db: Session = Depends(get_db),
):
    return calculate_working_capital_liquidity_bridge(db, request)


# MVP-15 through MVP-20 enterprise completion
@router.get("/global-treasury/cross-border-constraints", response_model=CrossBorderConstraintGraphOut)
def cross_border_constraints(db: Session = Depends(get_db)):
    return cross_border_constraint_graph(db)


@router.get("/optimization/legal-entity-liquidity", response_model=LegalEntityLiquidityOptimizationOut)
def legal_entity_liquidity_optimization(db: Session = Depends(get_db)):
    return optimize_legal_entity_liquidity(db)


@router.get("/integrations/readiness", response_model=ConnectorReadinessOut)
def connector_readiness(db: Session = Depends(get_db)):
    return enterprise_connector_readiness(db)


@router.get("/security/enterprise-posture", response_model=EnterpriseSecurityPostureOut)
def enterprise_security(db: Session = Depends(get_db)):
    return enterprise_security_posture(db)


@router.get("/models/validation-dashboard", response_model=ModelValidationDashboardOut)
def model_validation(db: Session = Depends(get_db)):
    return model_validation_dashboard(db)


@router.get("/workspaces/{role}", response_model=RoleWorkspaceOut)
def workspace(role: str, db: Session = Depends(get_db)):
    try:
        return role_workspace(db, role)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/production/readiness", response_model=ProductionReadinessOut)
def production_readiness_gate(db: Session = Depends(get_db)):
    return production_readiness(db)


# MVP-21 / MVP-22 final conceptual layers
@router.get("/intelligence/treasury-risk-radar", response_model=TreasuryRiskRadarOut)
def treasury_risk_radar(
    horizon_days: int = Query(90, ge=30, le=365),
    db: Session = Depends(get_db),
):
    return calculate_treasury_risk_radar(db, horizon_days)


@router.get("/strategy/optimal-liquidity-buffer", response_model=OptimalLiquidityBufferOut)
def optimal_liquidity_buffer(db: Session = Depends(get_db)):
    return calculate_optimal_liquidity_buffer(db)


@router.post("/strategy/treasury-plan", response_model=StrategicTreasuryPlanOut)
def strategic_treasury_plan(
    request: StrategicTreasuryRequest,
    db: Session = Depends(get_db),
):
    try:
        return optimize_strategic_treasury(db, request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# Production Phase 1: real-data integration and validation
@router.get("/integrations/phase1/status", response_model=ProductionPhase1StatusOut)
def phase1_status(db: Session = Depends(get_db)):
    return production_phase1_status(db)


@router.get("/integrations/phase1/mappings", response_model=list[ExternalMappingRow])
def phase1_mappings(connector_code: str | None = None, db: Session = Depends(get_db)):
    return list_external_mappings(db, connector_code)


@router.post("/integrations/phase1/mappings", response_model=ExternalMappingRow)
def phase1_create_mapping(request: ExternalMappingCreate, x_treasury_user: str = Depends(treasury_identity), db: Session = Depends(get_db)):
    return create_external_mapping(db, request)


@router.post("/integrations/phase1/bank/balances", response_model=IntegrationIngestionOut)
def phase1_bank_balances(request: CanonicalBankBatchIn, x_connector_name: str = Depends(connector_identity), db: Session = Depends(get_db)):
    if request.connector_code != x_connector_name:
        raise HTTPException(status_code=403, detail="Connector identity does not match connector_code")
    if request.schema_version != "1.0":
        raise HTTPException(status_code=422, detail="Unsupported canonical schema version")
    return ingest_bank_balances(db, request)


@router.post("/integrations/phase1/bank/transactions", response_model=IntegrationIngestionOut)
def phase1_bank_transactions(request: CanonicalBankTransactionBatchIn, x_connector_name: str = Depends(connector_identity), db: Session = Depends(get_db)):
    if request.connector_code != x_connector_name:
        raise HTTPException(status_code=403, detail="Connector identity does not match connector_code")
    if request.schema_version != "1.0":
        raise HTTPException(status_code=422, detail="Unsupported canonical schema version")
    return ingest_bank_transactions(db, request)


@router.post("/integrations/phase1/bank/iso20022", response_model=ISO20022IngestionOut)
def phase1_iso20022(request: ISO20022BankStatementIn, x_connector_name: str = Depends(connector_identity), db: Session = Depends(get_db)):
    if request.connector_code != x_connector_name:
        raise HTTPException(status_code=403, detail="Connector identity does not match connector_code")
    try:
        return ingest_iso20022_statement(db, request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/integrations/phase1/erp/cash-flows", response_model=IntegrationIngestionOut)
def phase1_erp_cashflows(request: CanonicalERPBatchIn, x_connector_name: str = Depends(connector_identity), db: Session = Depends(get_db)):
    if request.connector_code != x_connector_name:
        raise HTTPException(status_code=403, detail="Connector identity does not match connector_code")
    if request.schema_version != "1.0":
        raise HTTPException(status_code=422, detail="Unsupported canonical schema version")
    return ingest_erp_flows(db, request)


@router.post("/integrations/phase1/erp/journals", response_model=IntegrationIngestionOut)
def phase1_erp_journals(request: CanonicalERPJournalBatchIn, x_connector_name: str = Depends(connector_identity), db: Session = Depends(get_db)):
    if request.connector_code != x_connector_name:
        raise HTTPException(status_code=403, detail="Connector identity does not match connector_code")
    if request.schema_version != "1.0":
        raise HTTPException(status_code=422, detail="Unsupported canonical schema version")
    return ingest_erp_journals(db, request)


@router.post("/integrations/phase1/market/quotes", response_model=IntegrationIngestionOut)
def phase1_market_quotes(request: CanonicalMarketBatchIn, x_connector_name: str = Depends(connector_identity), db: Session = Depends(get_db)):
    if request.connector_code != x_connector_name:
        raise HTTPException(status_code=403, detail="Connector identity does not match connector_code")
    if request.schema_version != "1.0":
        raise HTTPException(status_code=422, detail="Unsupported canonical schema version")
    return ingest_market_quotes(db, request)


@router.post("/integrations/phase1/market/risk-data", response_model=IntegrationIngestionOut)
def phase1_market_risk(request: CanonicalMarketRiskBatchIn, x_connector_name: str = Depends(connector_identity), db: Session = Depends(get_db)):
    if request.connector_code != x_connector_name:
        raise HTTPException(status_code=403, detail="Connector identity does not match connector_code")
    if request.schema_version != "1.0":
        raise HTTPException(status_code=422, detail="Unsupported canonical schema version")
    return ingest_market_risk_data(db, request)


@router.post("/integrations/phase1/reconcile/bank-erp", response_model=DetailedReconciliationOut)
def phase1_reconcile_bank_erp(request: ReconciliationRequest, x_treasury_user: str = Depends(treasury_identity), db: Session = Depends(get_db)):
    try:
        return run_bank_erp_reconciliation(
            db, request.bank_connector_code, request.erp_connector_code, request.start_date, request.end_date,
            request.amount_tolerance, request.date_tolerance_days,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/integrations/phase1/runs", response_model=list[IntegrationRunOut])
def phase1_runs(limit: int = Query(50, ge=1, le=500), db: Session = Depends(get_db)):
    return list_integration_runs(db, limit)


@router.get("/integrations/phase1/lineage", response_model=list[DataLineageOut])
def phase1_lineage(connector_code: str | None = None, limit: int = Query(100, ge=1, le=1000), db: Session = Depends(get_db)):
    return list_lineage(db, connector_code, limit)


@router.get("/integrations/phase1/quarantine", response_model=list[QuarantineOut])
def phase1_quarantine(open_only: bool = True, limit: int = Query(100, ge=1, le=1000), db: Session = Depends(get_db)):
    return list_quarantine(db, open_only, limit)


@router.get("/integrations/phase1/coverage", response_model=RealDataCoverageOut)
def phase1_coverage(db: Session = Depends(get_db)):
    return real_data_coverage(db)


@router.patch("/integrations/phase1/certification/{connector_code}/{control_code}", response_model=IntegrationCertificationRow)
def phase1_update_certification(
    connector_code: str, control_code: str, request: IntegrationCertificationUpdate,
    x_treasury_user: str = Depends(treasury_identity), db: Session = Depends(get_db),
):
    try:
        return update_integration_certification(db, connector_code, control_code, request, x_treasury_user)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# Production Phase 1 v2: controlled shadow/parallel validation
@router.get("/integrations/phase1/authority", response_model=list[SourceAuthorityOut])
def phase1_source_authority(db: Session = Depends(get_db)):
    return list_source_authorities(db)


@router.patch("/integrations/phase1/authority/{connector_code}/{data_domain}", response_model=SourceAuthorityOut)
def phase1_update_source_authority(
    connector_code: str, data_domain: str, request: SourceAuthorityUpdate,
    x_treasury_user: str = Depends(treasury_identity), db: Session = Depends(get_db),
):
    try:
        return update_source_authority(db, connector_code, data_domain, request, x_treasury_user)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/integrations/phase1/shadow-records", response_model=list[ShadowRecordOut])
def phase1_shadow_records(
    connector_code: str | None = None, data_domain: str | None = None,
    limit: int = Query(100, ge=1, le=1000), db: Session = Depends(get_db),
):
    return list_shadow_records(db, connector_code, data_domain, limit)


@router.post("/integrations/phase1/data-quality/{connector_code}/{data_domain}", response_model=DataQualitySLAOut)
def phase1_data_quality(
    connector_code: str, data_domain: str, x_treasury_user: str = Depends(treasury_identity), db: Session = Depends(get_db),
):
    return evaluate_data_quality_sla(db, connector_code, data_domain)


@router.post("/integrations/phase1/parallel-run/observations", response_model=ParallelRunObservationOut)
def phase1_parallel_observation(
    request: ParallelRunObservationIn, x_treasury_user: str = Depends(treasury_identity), db: Session = Depends(get_db),
):
    try:
        return record_parallel_run_observation(db, request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/integrations/phase1/parallel-run/summary", response_model=ParallelRunSummaryOut)
def phase1_parallel_summary(
    connector_code: str | None = None, data_domain: str | None = None, window_days: int = Query(30, ge=10, le=120),
    db: Session = Depends(get_db),
):
    return parallel_run_summary(db, connector_code, data_domain, window_days)


@router.patch("/integrations/phase1/quarantine/{quarantine_id}/resolve", response_model=QuarantineOut)
def phase1_resolve_quarantine(
    quarantine_id: int, request: QuarantineResolutionIn, x_treasury_user: str = Depends(treasury_identity), db: Session = Depends(get_db),
):
    try:
        return resolve_quarantine_record(db, quarantine_id, request.resolution, x_treasury_user)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/integrations/phase1/parallel-readiness", response_model=ParallelReadinessOut)
def phase1_parallel_readiness(db: Session = Depends(get_db)):
    return parallel_readiness(db)
