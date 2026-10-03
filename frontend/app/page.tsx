import { MetricCard } from "../components/MetricCard";
import {
  getAgentRuntime,
  getCashMobility,
  getCashPools,
  getCrossBorderFunding,
  getCollateralLiquidity,
  getRefinancingRisk,
  getCounterpartyRisk,
  getDerivativeRisk,
  getForecast,
  getHedgeCoverage,
  getInterestRateRisk,
  getLiquidity,
  getMarketStress,
  getStressSummary,
  getTreasurySummary,
  getMarketDataControls,
  getConnectorControls,
  getReconciliations,
  getHedgeAccounting,
  getTransactionProposals,
  getScenarioTemplates,
  getReverseStress,
  getModelValidation,
  getModelDrift,
  getMLCashForecast,
  getIntradayLiquidity,
  getPaymentAnomalies,
  getIPV,
  getPaymentScreening,
  getInstitutionalValuation,
  getLiquidityAtRisk,
  getLegalNetting,
  getCollateralOptimization,
  getChampionChallenger,
  getOperationalResilience,
  getLiveOperationsStatus,
  getLiveTreasuryAlerts,
  getExecutionMessages,
  getHedgeOptimization,
  getFundingOptimization,
  getScenarioSearch,
  getTreasuryDecisionPack,
  getMarketRiskDistribution,
  getLiquidityTransferPricing,
  getBankAccountRationalization,
  getDigitalTwin,
  getHistoricalMarketCalibration,
  getHistoricalMarketRisk,
  getXVA,
  getLiquiditySurvival,
  getFundingConcentration,
  getRiskLimits,
  getTwinOptimization,
  getStructuralLiquidityGap,
  getRateGapDV01,
  getFundingTenorOptimization,
  getContingencyFundingPlan,
  getTreasuryEarlyWarning,
  getBalanceSheetTwin,
  getLiquidityConcentration,
  getProbabilisticLiquidity,
  getForecastDrivers,
  getForecastAccuracy,
  getForecastBias,
  getWorkingCapitalCycle,
  getReceivablesAging,
  getWorkingCapitalLiquidityBridge,
  getCrossBorderGraph,
  getLegalEntityLiquidityOptimization,
  getEnterpriseConnectorReadiness,
  getEnterpriseSecurityPosture,
  getProductionReadiness,
  getTreasurerWorkspace,
  getTreasuryRiskRadar,
  getOptimalLiquidityBuffer,
  getStrategicTreasuryPlan,
  getProductionPhase1Status,
  getProductionPhase1ParallelReadiness,
  getSourceAuthorities,
} from "../lib/api";

function money(value: string, ccy: string) {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: ccy, maximumFractionDigits: 0 }).format(Number(value));
}

function compactMoney(value: string, ccy: string) {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: ccy, notation: "compact", maximumFractionDigits: 1 }).format(Number(value));
}

function pct(value: string | null) {
  return value === null ? "n/a" : `${(Number(value) * 100).toFixed(1)}%`;
}

export default async function Home() {
  const [liq, summary, forecast, stress, derivativeRisk, hedges, rates, counterparties, marketStress, runtime, mobility, pools, intercompany, collateral, refinancing, marketFeeds, connectors, reconciliations, hedgeAccounting, proposals, scenarioTemplates, reverseStress, modelValidation, modelDrift, mlForecast, intraday, anomalies, ipv, screening, institutionalValuation, liquidityAtRisk, legalNetting, collateralOptimization, championChallenger, resilience, liveOps, liveAlerts, executionMessages, hedgeOptimization, fundingOptimization, scenarioSearch, decisionPack, marketDistribution, liquidityPricing, bankRationalization, digitalTwin, historicalCalibration, historicalRisk, xva, survival, fundingConcentration, riskLimits, twinOptimization, structuralGap, rateGapDV01, fundingTenor, contingencyPlan, earlyWarning, balanceSheetTwin, liquidityConcentration, probabilisticLiquidity, forecastDrivers, forecastAccuracy, forecastBias, workingCapital, receivablesAging, workingCapitalBridge, crossBorderGraph, entityLiquidityOptimization, enterpriseConnectors, enterpriseSecurity, productionReadiness, treasurerWorkspace] = await Promise.all([
    getLiquidity(),
    getTreasurySummary(),
    getForecast("BASE"),
    getStressSummary(),
    getDerivativeRisk(),
    getHedgeCoverage(),
    getInterestRateRisk(),
    getCounterpartyRisk(),
    getMarketStress(),
    getAgentRuntime(),
    getCashMobility(),
    getCashPools(),
    getCrossBorderFunding(),
    getCollateralLiquidity(),
    getRefinancingRisk(),
    getMarketDataControls(),
    getConnectorControls(),
    getReconciliations(),
    getHedgeAccounting(),
    getTransactionProposals(),
    getScenarioTemplates(),
    getReverseStress(),
    getModelValidation(),
    getModelDrift(),
    getMLCashForecast(),
    getIntradayLiquidity(),
    getPaymentAnomalies(),
    getIPV(),
    getPaymentScreening(),
    getInstitutionalValuation(),
    getLiquidityAtRisk(),
    getLegalNetting(),
    getCollateralOptimization(),
    getChampionChallenger(),
    getOperationalResilience(),
    getLiveOperationsStatus(),
    getLiveTreasuryAlerts(),
    getExecutionMessages(),
    getHedgeOptimization(),
    getFundingOptimization(),
    getScenarioSearch(),
    getTreasuryDecisionPack(),
    getMarketRiskDistribution(),
    getLiquidityTransferPricing(),
    getBankAccountRationalization(),
    getDigitalTwin(),
    getHistoricalMarketCalibration(),
    getHistoricalMarketRisk(),
    getXVA(),
    getLiquiditySurvival(),
    getFundingConcentration(),
    getRiskLimits(),
    getTwinOptimization(),
    getStructuralLiquidityGap(),
    getRateGapDV01(),
    getFundingTenorOptimization(),
    getContingencyFundingPlan(),
    getTreasuryEarlyWarning(),
    getBalanceSheetTwin(),
    getLiquidityConcentration(),
    getProbabilisticLiquidity(),
    getForecastDrivers(),
    getForecastAccuracy(),
    getForecastBias(),
    getWorkingCapitalCycle(),
    getReceivablesAging(),
    getWorkingCapitalLiquidityBridge(),
    getCrossBorderGraph(),
    getLegalEntityLiquidityOptimization(),
    getEnterpriseConnectorReadiness(),
    getEnterpriseSecurityPosture(),
    getProductionReadiness(),
    getTreasurerWorkspace(),
  ]);

  const [riskRadar, liquidityBuffer, strategicPlan, phase1, phase1Parallel, sourceAuthorities] = await Promise.all([
    getTreasuryRiskRadar(),
    getOptimalLiquidityBuffer(),
    getStrategicTreasuryPlan(),
    getProductionPhase1Status(),
    getProductionPhase1ParallelReadiness(),
    getSourceAuthorities(),
  ]);

  return (
    <main>
      <header className="hero">
        <div>
          <p className="eyebrow">GLOBAL TREASURY COMMAND CENTRE · PRODUCTION PHASE 1</p>
          <h1>Liquidity first. Risk visible.</h1>
          <p className="lead">Enterprise treasury-risk platform moving from synthetic MVP data into governed real-data integration, lineage, reconciliation and provider certification. Five Astra agent teams coordinate specialist deterministic engines; AI and optimizers remain non-executing.</p>
        </div>
        <div>
          <div className={`status status-${summary.overall_status.toLowerCase().replace(" ", "-")}`}>{summary.overall_status}</div>
          <div className="runtimeNote">{runtime.model} · {runtime.top_level_agents?.length ?? 5} top-level agents · {runtime.specialist_agents.length} specialist capabilities · LLM {runtime.llm_enabled ? "ON" : "SAFE-OFF"}</div>
        </div>
      </header>

      <section className="grid twoCol">
        <article className="panel noTopMargin">
          <p className="eyebrow">PRODUCTION PHASE 1 · REAL DATA INTEGRATION</p><h2>Integration control plane</h2>
          <div className="miniMetrics">
            <div><span>Phase status</span><strong>{phase1.overall_status}</strong></div>
            <div><span>Integration mode</span><strong>{phase1.integration_mode.toUpperCase()}</strong></div>
            <div><span>Certified connectors</span><strong>{phase1.certified_connector_count}</strong></div>
            <div><span>Open quarantine</span><strong className={phase1.open_quarantine_records ? "negative" : ""}>{phase1.open_quarantine_records}</strong></div>
            <div><span>24h successful runs</span><strong>{phase1.recent_successful_runs}</strong></div>
            <div><span>24h failed runs</span><strong className={phase1.recent_failed_runs ? "negative" : ""}>{phase1.recent_failed_runs}</strong></div>
          </div>
          <p className="muted compactCopy">Balances, ERP records and market inputs now carry source lineage, schema version, idempotency and reconciliation state before they become treasury inputs.</p>
        </article>
        <article className="panel noTopMargin">
          <p className="eyebrow">CONNECTOR CERTIFICATION</p><h2>Real-world gates remain explicit</h2>
          <div className="counterpartyList">{phase1.certification.slice(0, 6).map((x) => <div key={`${x.connector_code}-${x.control_code}`}><div><strong>{x.connector_code}</strong><small>{x.control_code}</small></div><div className="right"><strong className={x.status !== "PASS" ? "negative" : ""}>{x.status}</strong><small>{x.owner}</small></div></div>)}</div>
          <p className="muted compactCopy">A configured adapter is not treated as production-certified until provider authentication, schema, reconciliation, failover and volume controls are evidenced.</p>
        </article>
      </section>

      <section className="grid twoCol">
        <article className="panel noTopMargin">
          <p className="eyebrow">PRODUCTION PHASE 1 V2 · SHADOW VALIDATION</p><h2>Authority promotion gate</h2>
          <div className="miniMetrics">
            <div><span>Parallel readiness</span><strong>{phase1Parallel.status}</strong></div>
            <div><span>Active domains</span><strong>{phase1Parallel.active_authority_count}</strong></div>
            <div><span>Shadow domains</span><strong>{phase1Parallel.shadow_authority_count}</strong></div>
            <div><span>Parallel run</span><strong>{phase1Parallel.parallel_run_status}</strong></div>
          </div>
          <p className="muted compactCopy">Provider data remains non-authoritative until connector certification, data-quality SLAs and parallel-run evidence all pass.</p>
        </article>
        <article className="panel noTopMargin">
          <p className="eyebrow">SOURCE AUTHORITY</p><h2>Real feeds cannot silently take control</h2>
          <div className="counterpartyList">{sourceAuthorities.slice(0, 6).map((x) => <div key={`${x.connector_code}-${x.data_domain}`}><div><strong>{x.connector_code}</strong><small>{x.data_domain}</small></div><div className="right"><strong className={x.mode !== "ACTIVE" ? "negative" : ""}>{x.mode}</strong><small>{x.approved_by ?? "Awaiting promotion"}</small></div></div>)}</div>
        </article>
      </section>

      <section className="grid twoCol">
        <article className="panel noTopMargin">
          <p className="eyebrow">MVP-21 · TREASURY RISK RADAR</p><h2>Emerging risk before the standard report</h2>
          <div className="miniMetrics">
            <div><span>Radar status</span><strong className={riskRadar.overall_status === "RED" ? "negative" : ""}>{riskRadar.overall_status}</strong></div>
            <div><span>Deterioration score</span><strong>{pct(riskRadar.deterioration_score)}</strong></div>
            <div><span>Market regime</span><strong>{riskRadar.market_regime}</strong></div>
            <div><span>Survival horizon</span><strong>{riskRadar.survival_horizon_days} days</strong></div>
          </div>
          <p className="muted compactCopy">Modeled liquidity breach probability: <strong>{pct(riskRadar.liquidity_breach_probability)}</strong>. The deterioration score is a governed composite indicator, not a probability forecast.</p>
        </article>
        <article className="panel noTopMargin">
          <p className="eyebrow">MVP-22 · STRATEGIC TREASURY</p><h2>Multi-year funding, hedge and buffer planning</h2>
          <div className="miniMetrics">
            <div><span>Planning horizon</span><strong>{strategicPlan.horizon_years} years</strong></div>
            <div><span>Policy profile</span><strong>{strategicPlan.selected_strategy_code}</strong></div>
            <div><span>Liquidity buffer</span><strong>{compactMoney(liquidityBuffer.recommended_buffer, liquidityBuffer.reporting_currency)}</strong></div>
            <div><span>Execution authority</span><strong>{strategicPlan.execution_authority}</strong></div>
          </div>
          <div className="counterpartyList">{strategicPlan.strategies.map((x) => <div key={x.strategy_code}><div><strong>{x.strategy_code}</strong><small>Fixed {pct(x.target_fixed_rate_share)} · FX hedge {pct(x.target_fx_hedge_ratio)}</small></div><div className="right"><strong>{Number(x.resilience_score).toFixed(1)}</strong><small>{x.status}</small></div></div>)}</div>
        </article>
      </section>

      <section className="grid metrics">
        <MetricCard label="Gross Cash" value={money(liq.gross_cash, liq.reporting_currency)} />
        <MetricCard label="Deployable Cash" value={money(liq.deployable_cash, liq.reporting_currency)} />
        <MetricCard label="Undrawn Credit" value={money(liq.undrawn_credit, liq.reporting_currency)} />
        <MetricCard label="Liquidity Headroom" value={money(liq.liquidity_headroom, liq.reporting_currency)} sub="After minimum cash buffers" />
      </section>

      <section className="grid twoCol">
        <article className="panel noTopMargin">
          <p className="eyebrow">MVP-15 · GLOBAL LIQUIDITY ROUTING</p><h2>Cross-border liquidity under constraints</h2>
          <div className="miniMetrics">
            <div><span>Projected local deficit</span><strong>{compactMoney(entityLiquidityOptimization.local_deficit, entityLiquidityOptimization.reporting_currency)}</strong></div>
            <div><span>Proposed transfer</span><strong>{compactMoney(entityLiquidityOptimization.proposed_transfer, entityLiquidityOptimization.reporting_currency)}</strong></div>
            <div><span>Unresolved deficit</span><strong className={Number(entityLiquidityOptimization.unresolved_deficit) > 0 ? "negative" : ""}>{compactMoney(entityLiquidityOptimization.unresolved_deficit, entityLiquidityOptimization.reporting_currency)}</strong></div>
            <div><span>Blocked routes</span><strong>{crossBorderGraph.blocked_route_count}</strong></div>
          </div>
          <p className="muted compactCopy">Only cleared legal, regulatory and tax routes are eligible. Execution authority: <strong>{entityLiquidityOptimization.execution_authority}</strong>.</p>
        </article>
        <article className="panel noTopMargin">
          <p className="eyebrow">MVP-16–20 · ENTERPRISE GATE</p><h2>Integration, security and go-live readiness</h2>
          <div className="miniMetrics">
            <div><span>Ready connectors</span><strong>{enterpriseConnectors.ready_count}</strong></div>
            <div><span>Blocked connectors</span><strong className={enterpriseConnectors.blocked_count ? "negative" : ""}>{enterpriseConnectors.blocked_count}</strong></div>
            <div><span>Security posture</span><strong>{enterpriseSecurity.overall_status}</strong></div>
            <div><span>Production gate</span><strong className={productionReadiness.overall_status === "GO" ? "" : "negative"}>{productionReadiness.overall_status}</strong></div>
            <div><span>Readiness</span><strong>{pct(productionReadiness.readiness_pct)}</strong></div>
            <div><span>Treasurer work queue</span><strong>{treasurerWorkspace.open_items}</strong></div>
          </div>
          <p className="muted compactCopy">Deployment authority remains <strong>{productionReadiness.deployment_authority}</strong>; architecture readiness is never presented as production certification.</p>
        </article>
      </section>

      <section className="grid twoCol">
        <article className="panel noTopMargin">
          <p className="eyebrow">MVP-14 FORECAST CONTROL</p><h2>Forecast accuracy and liquidity bias</h2>
          <div className="miniMetrics">
            <div><span>WAPE</span><strong>{pct(forecastAccuracy.overall_wape)}</strong></div>
            <div><span>Cash bias</span><strong className={Number(forecastAccuracy.cash_bias_pct) > 0.05 ? "negative" : ""}>{pct(forecastAccuracy.cash_bias_pct)}</strong></div>
            <div><span>Status</span><strong>{forecastAccuracy.status}</strong></div>
            <div><span>Optimistic entities</span><strong>{forecastBias.optimistic_bias_entities}</strong></div>
          </div>
          <p className="muted compactCopy">Positive cash bias means forecasts historically overstated liquidity through higher expected collections and/or lower expected payments.</p>
        </article>
        <article className="panel noTopMargin">
          <p className="eyebrow">WORKING CAPITAL LIQUIDITY</p><h2>Cash conversion and collection pressure</h2>
          <div className="miniMetrics">
            <div><span>DSO</span><strong>{workingCapital.group_dso_days}d</strong></div>
            <div><span>DPO</span><strong>{workingCapital.group_dpo_days}d</strong></div>
            <div><span>Cash conversion cycle</span><strong>{workingCapital.group_ccc_days}d</strong></div>
            <div><span>Overdue AR</span><strong>{pct(receivablesAging.overdue_share)}</strong></div>
            <div><span>Illustrative cash release</span><strong>{compactMoney(workingCapitalBridge.total_modeled_cash_release, workingCapitalBridge.reporting_currency)}</strong></div>
            <div><span>Execution</span><strong>{workingCapitalBridge.execution_authority}</strong></div>
          </div>
          <p className="muted compactCopy">The working-capital bridge is scenario analysis only. Commercial terms and inventory policies remain human-owned operating decisions.</p>
        </article>
      </section>

      <section className="grid twoCol">
        <article className="panel noTopMargin">
          <p className="eyebrow">MVP-13 PROBABILISTIC LIQUIDITY</p><h2>Path risk, not just ending cash</h2>
          <div className="miniMetrics">
            <div><span>Any-buffer breach</span><strong className={Number(probabilisticLiquidity.probability_of_any_buffer_breach) >= 0.05 ? "negative" : ""}>{pct(probabilisticLiquidity.probability_of_any_buffer_breach)}</strong></div>
            <div><span>95% tail funding need</span><strong>{compactMoney(probabilisticLiquidity.tail_funding_need_95, probabilisticLiquidity.reporting_currency)}</strong></div>
            <div><span>P05 minimum headroom</span><strong>{compactMoney(probabilisticLiquidity.p05_minimum_headroom, probabilisticLiquidity.reporting_currency)}</strong></div>
            <div><span>Expected breach week</span><strong>{probabilisticLiquidity.expected_first_breach_week_if_breached ?? "n/a"}</strong></div>
          </div>
          <p className="muted compactCopy">Seeded Monte Carlo path simulation keeps percentile risk separate from deterministic forecasts and does not treat tail estimates as guaranteed maximum funding needs.</p>
        </article>
        <article className="panel noTopMargin">
          <p className="eyebrow">LIQUIDITY CONCENTRATION</p><h2>Where cash depends on a few nodes</h2>
          <div className="miniMetrics">
            <div><span>Trapped cash share</span><strong>{pct(liquidityConcentration.trapped_cash_share)}</strong></div>
            <div><span>Transferability ratio</span><strong>{pct(liquidityConcentration.transferability_ratio)}</strong></div>
            <div><span>Largest forecast driver</span><strong>{pct(forecastDrivers.largest_driver_share)}</strong></div>
            <div><span>Top-five flow share</span><strong>{pct(forecastDrivers.top_five_driver_share)}</strong></div>
          </div>
          <p className="muted compactCopy">Cash concentration and legal transferability are measured separately. Forecast-driver concentration highlights dependence on a small number of customer or supplier cash flows.</p>
        </article>
      </section>

      <section className="grid twoCol">
        <article className="panel noTopMargin">
          <p className="eyebrow">MVP-12 LIQUIDITY COMMAND</p><h2>Structural liquidity & contingency readiness</h2>
          <div className="miniMetrics">
            <div><span>Structural cash floor</span><strong>{compactMoney(structuralGap.minimum_cumulative_cash_before_facilities, structuralGap.reporting_currency)}</strong></div>
            <div><span>Minimum cash buffer</span><strong>{compactMoney(structuralGap.minimum_cash_buffer, structuralGap.reporting_currency)}</strong></div>
            <div><span>Contingency status</span><strong className={contingencyPlan.status === "CRISIS" ? "negative" : ""}>{contingencyPlan.status}</strong></div>
            <div><span>Tail funding need</span><strong>{compactMoney(contingencyPlan.reference_tail_funding_need, contingencyPlan.reporting_currency)}</strong></div>
          </div>
          <p className="muted compactCopy">Committed facilities remain contingent liquidity and are not counted as contractual cash. Contingency capacities are allocated sequentially to avoid double counting.</p>
        </article>
        <article className="panel noTopMargin">
          <p className="eyebrow">PREDICTIVE BALANCE-SHEET TWIN</p><h2>Rate, liquidity and early-warning state</h2>
          <div className="miniMetrics">
            <div><span>Twin state</span><strong className={balanceSheetTwin.status === "CRITICAL" ? "negative" : ""}>{balanceSheetTwin.status}</strong></div>
            <div><span>Stressed headroom</span><strong>{compactMoney(balanceSheetTwin.stressed_liquidity_headroom, balanceSheetTwin.reporting_currency)}</strong></div>
            <div><span>+100bp cash impact</span><strong>{compactMoney(rateGapDV01.annual_cash_impact_100bps, rateGapDV01.reporting_currency)}</strong></div>
            <div><span>Early warning</span><strong className={earlyWarning.overall_status === "RED" ? "negative" : ""}>{earlyWarning.overall_status}</strong></div>
          </div>
          <p className="muted compactCopy">Funding tenor objective: <strong>{fundingTenor.objective}</strong>. Proposed funding remains advisory with execution authority <strong>{fundingTenor.execution_authority}</strong>.</p>
        </article>
      </section>

      <section className="grid twoCol">
        <article className="panel noTopMargin">
          <p className="eyebrow">TREASURY DIGITAL TWIN</p><h2>Forward-looking enterprise state</h2>
          <div className="miniMetrics">
            <div><span>Twin state</span><strong className={digitalTwin.state === "STRESSED" ? "negative" : ""}>{digitalTwin.state}</strong></div>
            <div><span>Scenario headroom</span><strong>{compactMoney(digitalTwin.scenario_stressed_headroom, digitalTwin.reporting_currency)}</strong></div>
            <div><span>95% market VaR</span><strong>{compactMoney(marketDistribution.portfolio_var_95, marketDistribution.reporting_currency)}</strong></div>
            <div><span>90-day EaR</span><strong>{compactMoney(marketDistribution.earnings_at_risk_95_90d, marketDistribution.reporting_currency)}</strong></div>
          </div>
          <p className="muted compactCopy">Digital twin combines validated risk engines but keeps liquidity, market value, collateral, intraday and refinancing effects separately attributable.</p>
        </article>
        <article className="panel noTopMargin">
          <p className="eyebrow">LIQUIDITY ECONOMICS & BANK FOOTPRINT</p><h2>Scarcity pricing and account architecture</h2>
          <div className="miniMetrics">
            <div><span>Liquidity benchmark</span><strong>{pct(liquidityPricing.benchmark_rate)}</strong></div>
            <div><span>Deficit internal rate</span><strong>{pct(liquidityPricing.deficit_charge_rate)}</strong></div>
            <div><span>Bank accounts</span><strong>{bankRationalization.account_count}</strong></div>
            <div><span>Accounts for review</span><strong>{bankRationalization.review_candidate_count}</strong></div>
          </div>
          <p className="muted compactCopy">Largest bank share: <strong>{pct(bankRationalization.largest_bank_share)}</strong>. Internal liquidity pricing is management economics only, not tax transfer-pricing advice.</p>
        </article>
      </section>

      <section className="grid twoCol">
        <article className="panel noTopMargin">
          <p className="eyebrow">MVP-11 INSTITUTIONAL RISK</p><h2>History, survival & counterparty valuation</h2>
          <div className="miniMetrics">
            <div><span>Historical 10d VaR</span><strong>{compactMoney(historicalRisk.portfolio_var, historicalRisk.reporting_currency)}</strong></div>
            <div><span>Survival horizon</span><strong>{survival.survival_horizon_days} days</strong></div>
            <div><span>XVA-style sensitivity</span><strong>{compactMoney(xva.total_xva_style_adjustment, xva.reporting_currency)}</strong></div>
            <div><span>Risk limits</span><strong className={riskLimits.breach_count ? "negative" : ""}>{riskLimits.overall_status}</strong></div>
          </div>
          <p className="muted compactCopy">EWMA calibration uses {historicalCalibration.lookback_observations} governed observations across {historicalCalibration.factors.length} FX factors. XVA remains a treasury sensitivity until independently validated for accounting use.</p>
        </article>
        <article className="panel noTopMargin">
          <p className="eyebrow">FUNDING & DIGITAL-TWIN OPTIMIZATION</p><h2>Concentration and resilient configurations</h2>
          <div className="miniMetrics">
            <div><span>Top lender</span><strong>{fundingConcentration.top_lender ?? "n/a"}</strong></div>
            <div><span>Top lender share</span><strong>{pct(fundingConcentration.top_lender_share)}</strong></div>
            <div><span>Funding HHI</span><strong>{Number(fundingConcentration.hhi).toFixed(3)}</strong></div>
            <div><span>Twin configurations</span><strong>{twinOptimization.combinations_tested}</strong></div>
          </div>
          <p className="muted compactCopy">Selected grid configuration has execution authority <strong>{twinOptimization.execution_authority}</strong>. Optimization is decision support only and cannot create treasury transactions.</p>
        </article>
      </section>

      <section className="grid twoCol">
        <article className="panel noTopMargin">
          <p className="eyebrow">TREASURY DECISION INTELLIGENCE</p><h2>Governed strategy comparison</h2>
          <div className="miniMetrics">
            <div><span>Decision objective</span><strong>{decisionPack.decision_objective}</strong></div>
            <div><span>Selected policy profile</span><strong>{decisionPack.recommended_strategy_code}</strong></div>
            <div><span>Strategies compared</span><strong>{decisionPack.strategies.length}</strong></div>
            <div><span>Execution authority</span><strong>{decisionPack.execution_authority}</strong></div>
          </div>
          <div className="counterpartyList">{decisionPack.strategies.map((x) => <div key={x.strategy_code}><div><strong>{x.strategy_code}</strong><small>Hedge {pct(x.hedge_target_ratio)} · mobilize {pct(x.cash_mobilization_pct)}</small></div><div className="right"><strong>{Number(x.resilience_score).toFixed(1)}</strong><small>{x.decision_status}</small></div></div>)}</div>
        </article>
        <article className="panel noTopMargin">
          <p className="eyebrow">OPTIMIZATION ENGINES</p><h2>Hedge, funding & scenario search</h2>
          <div className="miniMetrics">
            <div><span>Incremental hedge</span><strong>{compactMoney(hedgeOptimization.total_incremental_hedge_reporting, hedgeOptimization.reporting_currency)}</strong></div>
            <div><span>Tail funding need</span><strong>{compactMoney(fundingOptimization.requested_funding_need, fundingOptimization.reporting_currency)}</strong></div>
            <div><span>Uncovered funding</span><strong className={Number(fundingOptimization.uncovered_funding) > 0 ? "negative" : ""}>{compactMoney(fundingOptimization.uncovered_funding, fundingOptimization.reporting_currency)}</strong></div>
            <div><span>Stress combinations</span><strong>{scenarioSearch.combinations_tested}</strong></div>
          </div>
          <p className="muted compactCopy">{scenarioSearch.breach_count} configured stress combinations breach liquidity. Worst stressed headroom: <strong>{compactMoney(scenarioSearch.worst_stressed_headroom, scenarioSearch.reporting_currency)}</strong>. Grid-search outcomes are scenarios, not probabilities.</p>
        </article>
      </section>

      <section className="grid twoCol">
        <article className="panel noTopMargin">
          <p className="eyebrow">LIVE TREASURY OPERATIONS</p><h2>Event ledger & stream health</h2>
          <div className="miniMetrics">
            <div><span>24h events</span><strong>{liveOps.events_24h}</strong></div>
            <div><span>Quarantined / failed</span><strong className={(liveOps.quarantined_24h + liveOps.failed_24h) ? "negative" : ""}>{liveOps.quarantined_24h + liveOps.failed_24h}</strong></div>
            <div><span>Max event lag</span><strong>{liveOps.max_event_lag_seconds}s</strong></div>
            <div><span>Stream status</span><strong>{liveOps.status}</strong></div>
          </div>
          <div className="counterpartyList">{liveOps.checkpoints.map((c) => <div key={c.connector_name}><div><strong>{c.connector_name}</strong><small>{c.source_system}</small></div><div className="right"><strong>{c.status}</strong><small>{c.lag_seconds ?? 0}s lag</small></div></div>)}</div>
        </article>
        <article className="panel noTopMargin">
          <p className="eyebrow">CONTINUOUS MONITORING</p><h2>Alerts & execution acknowledgements</h2>
          <div className="miniMetrics">
            <div><span>Open alerts</span><strong className={liveOps.critical_alerts ? "negative" : ""}>{liveOps.open_alerts}</strong></div>
            <div><span>Critical alerts</span><strong className={liveOps.critical_alerts ? "negative" : ""}>{liveOps.critical_alerts}</strong></div>
            <div><span>Execution messages</span><strong>{executionMessages.length}</strong></div>
            <div><span>Awaiting acknowledgement</span><strong>{executionMessages.filter((m) => ["QUEUED", "SENT"].includes(m.status)).length}</strong></div>
          </div>
          <div className="counterpartyList">{liveAlerts.slice(0, 4).map((a) => <div key={a.id}><div><strong>{a.title}</strong><small>{a.category}</small></div><div className="right"><strong>{a.severity}</strong><small>{a.status}</small></div></div>)}</div>
          <p className="muted compactCopy">Continuous monitoring can raise and refresh alerts. It cannot create, approve, release or execute treasury transactions.</p>
        </article>
      </section>

      <section className="grid twoCol">
        <article className="panel noTopMargin">
          <p className="eyebrow">INSTITUTIONAL RISK</p><h2>Liquidity-at-Risk & Cash-Flow-at-Risk</h2>
          <div className="miniMetrics">
            <div><span>95% LaR</span><strong>{compactMoney(liquidityAtRisk.liquidity_at_risk, liquidityAtRisk.reporting_currency)}</strong></div>
            <div><span>CFaR</span><strong>{compactMoney(liquidityAtRisk.cash_flow_at_risk, liquidityAtRisk.reporting_currency)}</strong></div>
            <div><span>Buffer-breach probability</span><strong className={Number(liquidityAtRisk.probability_of_buffer_breach) > 0.05 ? "negative" : ""}>{(Number(liquidityAtRisk.probability_of_buffer_breach) * 100).toFixed(1)}%</strong></div>
            <div><span>99% tail funding need</span><strong>{compactMoney(liquidityAtRisk.tail_funding_need, liquidityAtRisk.reporting_currency)}</strong></div>
          </div>
        </article>
        <article className="panel noTopMargin">
          <p className="eyebrow">GOVERNED VALUATION</p><h2>Curves, vol and model-value control</h2>
          <div className="miniMetrics">
            <div><span>Priced trades</span><strong>{institutionalValuation.priced_trade_count}</strong></div>
            <div><span>Unpriced</span><strong className={institutionalValuation.unpriced_trade_count ? "negative" : ""}>{institutionalValuation.unpriced_trade_count}</strong></div>
            <div><span>Model/book difference</span><strong>{compactMoney(institutionalValuation.aggregate_difference, institutionalValuation.reporting_currency)}</strong></div>
            <div><span>Legal netting benefit</span><strong>{compactMoney(legalNetting.total_netting_benefit, legalNetting.reporting_currency)}</strong></div>
          </div>
        </article>
      </section>

      <section className="grid twoCol">
        <article className="panel noTopMargin">
          <p className="eyebrow">LEGAL NETTING & COLLATERAL</p><h2>Counterparty exposure infrastructure</h2>
          <div className="miniMetrics">
            <div><span>Enforceable sets</span><strong>{legalNetting.legally_enforceable_sets}</strong></div>
            <div><span>Legal review required</span><strong className={legalNetting.review_required_sets ? "negative" : ""}>{legalNetting.review_required_sets}</strong></div>
            <div><span>Additional collateral</span><strong>{compactMoney(collateralOptimization.total_additional_collateral_required, collateralOptimization.reporting_currency)}</strong></div>
            <div><span>Cross-ccy funding</span><strong>{compactMoney(collateralOptimization.total_cross_currency_funding_required, collateralOptimization.reporting_currency)}</strong></div>
          </div>
        </article>
        <article className="panel noTopMargin">
          <p className="eyebrow">MODEL & RESILIENCE GOVERNANCE</p><h2>No silent promotion. No invisible failure.</h2>
          <div className="miniMetrics">
            <div><span>Model decision</span><strong>{championChallenger.recommendation}</strong></div>
            <div><span>Auto-promotion</span><strong>{championChallenger.auto_promotion_allowed ? "ENABLED" : "BLOCKED"}</strong></div>
            <div><span>Tier-1 resilience gaps</span><strong className={resilience.tier1_gaps ? "negative" : ""}>{resilience.tier1_gaps}</strong></div>
            <div><span>Resilience status</span><strong>{resilience.overall_status}</strong></div>
          </div>
        </article>
      </section>

      <section className="panel">
        <div className="sectionTitle"><div><p className="eyebrow">13-WEEK FORECAST</p><h2>Base-case liquidity path</h2></div>
          <div className="forecastMeta">Ending headroom <strong>{compactMoney(forecast.ending_liquidity_headroom, forecast.reporting_currency)}</strong></div>
        </div>
        <div className="forecastStrip">
          {forecast.points.map((p) => {
            const headroom = Number(p.liquidity_headroom);
            const scale = Math.min(100, Math.max(4, Math.abs(headroom) / 120000000 * 100));
            return <div className="week" key={p.week} title={`Week ${p.week}: ${money(p.liquidity_headroom, forecast.reporting_currency)}`}>
              <div className={`weekBar ${headroom < 0 ? "weekBarDanger" : ""}`} style={{height: `${scale}%`}} />
              <small>W{p.week}</small>
            </div>;
          })}
        </div>
        <div className="tableWrap"><table><thead><tr><th>Week</th><th>Inflows</th><th>Outflows</th><th>Closing cash</th><th>Liquidity headroom</th></tr></thead>
          <tbody>{forecast.points.map((p) => <tr key={p.week}><td>W{p.week}</td><td>{compactMoney(p.expected_inflows, forecast.reporting_currency)}</td><td>{compactMoney(p.expected_outflows, forecast.reporting_currency)}</td><td>{compactMoney(p.closing_cash, forecast.reporting_currency)}</td><td className={Number(p.liquidity_headroom) < 0 ? "negative" : ""}>{compactMoney(p.liquidity_headroom, forecast.reporting_currency)}</td></tr>)}</tbody>
        </table></div>
      </section>

      <section className="panel">
        <p className="eyebrow">STRESS TEST</p><h2>Liquidity resilience</h2>
        <div className="grid stressGrid">
          {stress.map((s) => <article className={`stressCard ${s.first_buffer_breach_week ? "stressCardDanger" : ""}`} key={s.scenario}>
            <div className="stressTop"><strong>{s.scenario_label}</strong><span>{s.first_buffer_breach_week ? `Breach W${s.first_buffer_breach_week}` : "Buffer maintained"}</span></div>
            <p>{compactMoney(s.minimum_headroom, liq.reporting_currency)}</p><small>Minimum liquidity headroom</small>
            {Number(s.maximum_shortfall) > 0 && <div className="shortfall">Max shortfall {compactMoney(s.maximum_shortfall, liq.reporting_currency)}</div>}
          </article>)}
        </div>
      </section>

      <section className="grid twoCol">
        <article className="panel noTopMargin">
          <p className="eyebrow">PREDICTIVE LIQUIDITY</p><h2>ML cash forecast & model risk</h2>
          <div className="miniMetrics">
            <div><span>Validation</span><strong>{modelValidation.validation_status}</strong></div>
            <div><span>Delay MAE</span><strong>{Number(modelValidation.mae_delay_days).toFixed(1)} days</strong></div>
            <div><span>Model drift</span><strong className={modelDrift.status === "HIGH" ? "negative" : ""}>{modelDrift.status}</strong></div>
            <div><span>Conservative headroom</span><strong>{compactMoney(mlForecast.conservative_ending_headroom, mlForecast.reporting_currency)}</strong></div>
          </div>
          <p className="muted compactCopy">Random-forest payment timing model with holdout validation, uncertainty bands and drift monitoring. ML never changes source cash flows automatically.</p>
        </article>
        <article className="panel noTopMargin">
          <p className="eyebrow">INTRADAY LIQUIDITY</p><h2>Payment queue & funding peak</h2>
          <div className="miniMetrics">
            <div><span>Entity</span><strong>{intraday.entity_name}</strong></div>
            <div><span>Peak funding need</span><strong className={Number(intraday.peak_intraday_funding_need) > 0 ? "negative" : ""}>{compactMoney(intraday.peak_intraday_funding_need, intraday.reporting_currency)}</strong></div>
            <div><span>First breach</span><strong>{intraday.first_buffer_breach_bucket ?? "None"}</strong></div>
            <div><span>Anomalies</span><strong className={anomalies.length ? "negative" : ""}>{anomalies.length}</strong></div>
          </div>
        </article>
      </section>

      <section className="grid twoCol">
        <article className="panel noTopMargin">
          <p className="eyebrow">INDEPENDENT VALUATION</p><h2>Derivative IPV</h2>
          <div className="miniMetrics">
            <div><span>Pass</span><strong>{ipv.pass_count}</strong></div><div><span>Warnings</span><strong>{ipv.warning_count}</strong></div>
            <div><span>Failures</span><strong className={ipv.fail_count ? "negative" : ""}>{ipv.fail_count}</strong></div><div><span>Missing</span><strong>{ipv.missing_count}</strong></div>
          </div>
        </article>
        <article className="panel noTopMargin">
          <p className="eyebrow">PAYMENT SCREENING</p><h2>Execution blocks</h2>
          <div className="counterpartyList">{screening.map((x) => <div key={x.payment_reference}><div><strong>{x.counterparty}</strong><small>{x.payment_reference}</small></div><div className="right"><strong className={x.execution_blocked ? "negative" : ""}>{x.status}</strong><small>{x.execution_blocked ? "BLOCK" : "CLEAR"}</small></div></div>)}</div>
        </article>
      </section>

      <section className="grid twoCol">
        <article className="panel noTopMargin">
          <p className="eyebrow">DERIVATIVES</p><h2>Hedge book & MTM</h2>
          <div className="miniMetrics">
            <div><span>Open trades</span><strong>{derivativeRisk.open_trade_count}</strong></div>
            <div><span>Notional</span><strong>{compactMoney(derivativeRisk.total_notional_reporting, derivativeRisk.reporting_currency)}</strong></div>
            <div><span>Net MTM</span><strong>{compactMoney(derivativeRisk.net_market_value_reporting, derivativeRisk.reporting_currency)}</strong></div>
            <div><span>Unmapped</span><strong className={derivativeRisk.unmapped_trade_count ? "negative" : ""}>{derivativeRisk.unmapped_trade_count}</strong></div>
          </div>
          <div className="bucketList">{derivativeRisk.maturity_buckets.map((b) => <div key={b.bucket}><span>{b.bucket}</span><strong>{b.trade_count} trades</strong><small>{compactMoney(b.notional_reporting, derivativeRisk.reporting_currency)}</small></div>)}</div>
        </article>

        <article className="panel noTopMargin">
          <p className="eyebrow">MARKET-RISK LIQUIDITY</p><h2>Adverse market overlay</h2>
          <div className="miniMetrics">
            <div><span>10% FX shock</span><strong>{compactMoney(marketStress.estimated_fx_adverse_change, marketStress.reporting_currency)}</strong></div>
            <div><span>+100 bps annual cash</span><strong>{compactMoney(marketStress.annual_rate_cash_impact, marketStress.reporting_currency)}</strong></div>
            <div><span>Near-term negative MTM</span><strong>{compactMoney(marketStress.near_term_derivative_negative_mtm, marketStress.reporting_currency)}</strong></div>
            <div><span>Combined overlay</span><strong>{compactMoney(marketStress.combined_market_liquidity_call, marketStress.reporting_currency)}</strong></div>
          </div>
          <p className="muted compactCopy">This overlay is kept separate from operating cash forecasts to avoid double counting.</p>
        </article>
      </section>

      <section className="panel">
        <p className="eyebrow">FX HEDGE CONTROL</p><h2>Residual exposure and policy coverage</h2>
        <div className="tableWrap"><table><thead><tr><th>Currency</th><th>Underlying</th><th>Hedge</th><th>Coverage</th><th>Residual</th><th>Status</th></tr></thead><tbody>
          {hedges.map((h) => <tr key={h.currency}><td>{h.currency}</td><td>{compactMoney(h.underlying_exposure, h.currency)}</td><td>{compactMoney(h.hedge_notional, h.currency)}</td><td>{pct(h.hedge_ratio)}</td><td>{compactMoney(h.residual_exposure, h.currency)}</td><td><span className={`riskPill ${h.status !== "WITHIN-POLICY" ? "riskPillWarn" : ""}`}>{h.status}</span></td></tr>)}
        </tbody></table></div>
      </section>

      <section className="grid twoCol">
        <article className="panel noTopMargin">
          <p className="eyebrow">INTEREST-RATE RISK</p><h2>Debt sensitivity</h2>
          <div className="miniMetrics">
            <div><span>Total debt</span><strong>{compactMoney(rates.total_debt, rates.reporting_currency)}</strong></div>
            <div><span>Floating before hedges</span><strong>{pct(rates.floating_share_before_hedges)}</strong></div>
            <div><span>Floating after hedges</span><strong>{pct(rates.floating_share_after_hedges)}</strong></div>
            <div><span>+100 bps cash impact</span><strong>{compactMoney(rates.annual_cash_impact_100bps, rates.reporting_currency)}</strong></div>
          </div>
        </article>

        <article className="panel noTopMargin">
          <p className="eyebrow">COUNTERPARTY RISK</p><h2>Derivative credit limits</h2>
          <div className="counterpartyList">{counterparties.map((c) => <div key={c.counterparty}><div><strong>{c.counterparty}</strong><small>{c.credit_rating ?? "Unrated"}</small></div><div className="right"><strong>{pct(c.utilization)}</strong><small>{c.status}</small></div></div>)}</div>
        </article>
      </section>


      <section className="grid twoCol">
        <article className="panel noTopMargin">
          <p className="eyebrow">CASH MOBILITY</p><h2>Transferable vs trapped cash</h2>
          <div className="miniMetrics">
            <div><span>Transferable surplus</span><strong>{compactMoney(mobility.total_transferable_surplus, mobility.reporting_currency)}</strong></div>
            <div><span>Trapped cash</span><strong>{compactMoney(mobility.total_trapped_cash, mobility.reporting_currency)}</strong></div>
            <div><span>Local cash deficit</span><strong>{compactMoney(mobility.total_local_cash_deficit, mobility.reporting_currency)}</strong></div>
            <div><span>Pool offset capacity</span><strong>{pools[0] ? compactMoney(pools[0].internal_offset_capacity, pools[0].currency) : "n/a"}</strong></div>
          </div>
          <p className="muted compactCopy">Mobility restrictions sit on top of ordinary bank restrictions and local operating buffers.</p>
        </article>

        <article className="panel noTopMargin">
          <p className="eyebrow">COLLATERAL LIQUIDITY</p><h2>CSA and margin-call buffer</h2>
          <div className="miniMetrics">
            <div><span>Current margin call</span><strong>{compactMoney(collateral.current_margin_call, collateral.reporting_currency)}</strong></div>
            <div><span>Stressed margin call</span><strong>{compactMoney(collateral.stressed_margin_call, collateral.reporting_currency)}</strong></div>
            <div><span>Counterparties</span><strong>{collateral.rows.length}</strong></div>
            <div><span>Calls / watches</span><strong>{collateral.rows.filter((r) => r.status !== "OK").length}</strong></div>
          </div>
        </article>
      </section>

      <section className="grid twoCol">
        <article className="panel noTopMargin">
          <p className="eyebrow">CROSS-BORDER FUNDING</p><h2>Intercompany capacity with tax controls</h2>
          <div className="tableWrap"><table><thead><tr><th>Route</th><th>Capacity</th><th>Rate</th><th>TP</th><th>Tax status</th></tr></thead><tbody>
            {intercompany.map((f) => <tr key={f.facility_id}><td>{f.lender_entity} → {f.borrower_entity}</td><td>{compactMoney(f.available_amount_reporting, liq.reporting_currency)}</td><td>{pct(f.interest_rate)}</td><td>{f.transfer_pricing_status}</td><td>{f.tax_rule_status}</td></tr>)}
          </tbody></table></div>
        </article>

        <article className="panel noTopMargin">
          <p className="eyebrow">REFINANCING & COVENANTS</p><h2>Forward funding risk</h2>
          <div className="miniMetrics">
            <div><span>Debt due 180d</span><strong>{compactMoney(refinancing.debt_due_180d, refinancing.reporting_currency)}</strong></div>
            <div><span>Facilities expiring 90d</span><strong>{compactMoney(refinancing.committed_facilities_due_90d, refinancing.reporting_currency)}</strong></div>
            <div><span>Covenant warnings</span><strong>{refinancing.covenants.filter((c) => c.status === "WARNING").length}</strong></div>
            <div><span>Covenant breaches</span><strong className={refinancing.covenants.some((c) => c.status === "BREACH") ? "negative" : ""}>{refinancing.covenants.filter((c) => c.status === "BREACH").length}</strong></div>
          </div>
        </article>
      </section>

      <section className="grid twoCol">
        <article className="panel noTopMargin">
          <p className="eyebrow">EXECUTION CONTROLS</p><h2>Data and reconciliation readiness</h2>
          <div className="miniMetrics">
            <div><span>Primary feeds usable</span><strong>{marketFeeds.filter((f) => f.source_type === "PRIMARY" && f.execution_usable).length}/{marketFeeds.filter((f) => f.source_type === "PRIMARY").length}</strong></div>
            <div><span>Required connectors usable</span><strong>{connectors.filter((c) => c.execution_usable).length}/{connectors.length}</strong></div>
            <div><span>Recon warnings</span><strong>{reconciliations.filter((r) => r.status === "WARN").length}</strong></div>
            <div><span>Recon failures</span><strong className={reconciliations.some((r) => r.status === "FAIL") ? "negative" : ""}>{reconciliations.filter((r) => r.status === "FAIL").length}</strong></div>
          </div>
          <div className="counterpartyList">{marketFeeds.map((f) => <div key={f.feed_name}><div><strong>{f.feed_name}</strong><small>{f.asset_class} · {f.source_type}</small></div><div className="right"><strong>{f.execution_usable ? "USABLE" : "STALE"}</strong><small>{f.age_minutes}m old</small></div></div>)}</div>
        </article>

        <article className="panel noTopMargin">
          <p className="eyebrow">MAKER-CHECKER</p><h2>Transaction approval queue</h2>
          <div className="miniMetrics">
            <div><span>Open proposals</span><strong>{proposals.filter((p) => !["REJECTED", "RELEASED_FOR_EXECUTION"].includes(p.status)).length}</strong></div>
            <div><span>Pending approval</span><strong>{proposals.filter((p) => ["PENDING_APPROVAL", "PARTIALLY_APPROVED"].includes(p.status)).length}</strong></div>
            <div><span>Control blocked</span><strong className={proposals.some((p) => p.control_status === "BLOCKED") ? "negative" : ""}>{proposals.filter((p) => p.control_status === "BLOCKED").length}</strong></div>
            <div><span>Released</span><strong>{proposals.filter((p) => p.status === "RELEASED_FOR_EXECUTION").length}</strong></div>
          </div>
          <div className="tableWrap"><table><thead><tr><th>Type</th><th>Amount</th><th>Status</th><th>Approvals</th></tr></thead><tbody>
            {proposals.slice(0, 5).map((p) => <tr key={p.id}><td>{p.proposal_type}</td><td>{compactMoney(p.amount_reporting, liq.reporting_currency)}</td><td>{p.status}</td><td>{p.approval_count}/{p.required_approvals}</td></tr>)}
          </tbody></table></div>
        </article>
      </section>

      <section className="grid twoCol">
        <article className="panel noTopMargin">
          <p className="eyebrow">HEDGE ACCOUNTING</p><h2>Designation control</h2>
          <div className="miniMetrics">
            <div><span>Designations</span><strong>{hedgeAccounting.length}</strong></div>
            <div><span>Ready</span><strong>{hedgeAccounting.filter((h) => h.control_status === "READY").length}</strong></div>
            <div><span>Documentation gaps</span><strong>{hedgeAccounting.filter((h) => h.control_status === "DOCUMENTATION_GAP").length}</strong></div>
            <div><span>Effectiveness review</span><strong>{hedgeAccounting.filter((h) => h.control_status === "EFFECTIVENESS_REVIEW").length}</strong></div>
          </div>
          <p className="muted compactCopy">Economic hedge risk and accounting designation remain separate control layers.</p>
        </article>

        <article className="panel noTopMargin">
          <p className="eyebrow">REVERSE STRESS</p><h2>How much collection stress breaks the buffer?</h2>
          <div className="miniMetrics">
            <div><span>Collection haircut</span><strong>{Number(reverseStress.collection_haircut_pct).toFixed(1)}%</strong></div>
            <div><span>First breach</span><strong>{reverseStress.first_buffer_breach_week ? `W${reverseStress.first_buffer_breach_week}` : "None"}</strong></div>
            <div><span>Facility availability</span><strong>{pct(reverseStress.facility_availability)}</strong></div>
            <div><span>Scenario library</span><strong>{scenarioTemplates.length}</strong></div>
          </div>
          <p className="muted compactCopy">The reverse-stress search is deterministic. It finds a break point; it does not estimate probability.</p>
        </article>
      </section>

      <section className="panel">
        <div className="sectionTitle"><div><p className="eyebrow">ENTITY VIEW</p><h2>Liquidity by legal entity</h2></div></div>
        <div className="tableWrap"><table><thead><tr><th>Entity</th><th>Deployable cash</th><th>Undrawn credit</th><th>Headroom</th></tr></thead><tbody>
          {liq.entities.map((e) => <tr key={e.entity_id}><td>{e.entity_name}<span className="tag">{e.local_currency}</span></td><td>{money(e.deployable_cash_reporting, liq.reporting_currency)}</td><td>{money(e.undrawn_credit_reporting, liq.reporting_currency)}</td><td>{money(e.liquidity_headroom_reporting, liq.reporting_currency)}</td></tr>)}
        </tbody></table></div>
      </section>

      <section className="panel">
        <p className="eyebrow">SPECIALIST AGENTS · {summary.ai_model}</p><h2>Treasury findings</h2>
        <div className="agentRail">{runtime.specialist_agents.map((a) => <span key={a}>{a}</span>)}</div>
        <div className="findings">{summary.findings.map((f, i) => <article className="finding" key={`${f.agent}-${i}`}><div><span className={`severity severity-${f.severity.toLowerCase()}`}>{f.severity}</span><strong>{f.title}</strong></div><p>{f.message}</p><small>{f.agent}{f.metric ? ` · ${f.metric}` : ""}</small></article>)}</div>
      </section>
    </main>
  );
}
