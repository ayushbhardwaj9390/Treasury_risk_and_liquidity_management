from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    BankAccount, CashFlow, CounterpartyLimit, CreditFacility, DebtPosition, DerivativePosition, FXRate, LegalEntity, TreasuryPolicy,
    CashRestriction, CashPool, CashPoolMember, IntercompanyFacility, TaxRule, CollateralAgreement, CovenantTest,
    UserAccount, MarketDataFeed, SourceConnector, ReconciliationRun, HedgeAccountingDesignation, TransactionProposal, ScenarioTemplate,
    PaymentHistory, IntradayPayment, IndependentValuation, PaymentScreeningCase,
    DerivativeValuationTerms, MarketCurvePoint, VolatilityQuote, LegalNettingSet, NettingSetTrade, ModelDeployment, ResilienceControl,
    TreasuryEvent, ConnectorCheckpoint, LiveTreasuryAlert,
    MarketReturnObservation, CounterpartyCreditMetric, TreasuryRiskLimit,
    ForecastPerformanceRecord, WorkingCapitalObservation,
    CrossBorderConstraint, EnterpriseConnectorProfile, SecurityControlRecord,
    ModelValidationRecord, InvestigationCase, DeploymentReadinessControl, ModelRegistryEntry,
    ExternalReferenceMap, IntegrationCertificationControl, SourceAuthorityPolicy,
)


def _seed_forecast_demo(db: Session) -> None:
    if db.scalar(select(CashFlow.id).where(CashFlow.counterparty.like("Forecast Demo%" )).limit(1)):
        return

    entities = db.scalars(select(LegalEntity)).all()
    e = {x.country_code: x for x in entities}
    if not all(code in e for code in ("IN", "US", "DE", "SG", "GB", "JP")):
        return

    # Synthetic 13-week operating plan. Amounts are deliberately varied so stress testing
    # can expose a liquidity vulnerability without making the base case insolvent.
    receivables_usd = [12, 11, 14, 10, 13, 12, 15, 10, 12, 14, 11, 13, 15]
    payables_usd = [9, 10, 10, 11, 9, 10, 11, 10, 12, 9, 10, 10, 11]
    probabilities = [Decimal("0.96"), Decimal("0.94"), Decimal("0.95"), Decimal("0.90"), Decimal("0.93"), Decimal("0.95"), Decimal("0.92"), Decimal("0.91"), Decimal("0.94"), Decimal("0.95"), Decimal("0.90"), Decimal("0.93"), Decimal("0.96")]

    for i in range(13):
        due = date.today() + timedelta(days=i * 7 + 3)
        db.add(CashFlow(
            entity_id=e["US"].id,
            flow_type="RECEIVABLE",
            counterparty=f"Forecast Demo Customer W{i+1}",
            currency="USD",
            amount=Decimal(receivables_usd[i]) * Decimal("1000000"),
            due_date=due,
            probability=probabilities[i],
        ))
        db.add(CashFlow(
            entity_id=e["US"].id,
            flow_type="PAYABLE",
            counterparty=f"Forecast Demo Supplier W{i+1}",
            currency="USD",
            amount=Decimal(payables_usd[i]) * Decimal("1000000"),
            due_date=due + timedelta(days=1),
            probability=Decimal("1"),
        ))

    # Known lumpy treasury obligations.
    db.add_all([
        CashFlow(entity_id=e["US"].id, flow_type="PAYABLE", counterparty="Forecast Demo Debt Maturity", currency="USD", amount=Decimal("22000000"), due_date=date.today()+timedelta(days=52), probability=Decimal("1")),
        CashFlow(entity_id=e["DE"].id, flow_type="PAYABLE", counterparty="Forecast Demo Quarterly Tax", currency="EUR", amount=Decimal("7000000"), due_date=date.today()+timedelta(days=66), probability=Decimal("1")),
        CashFlow(entity_id=e["IN"].id, flow_type="RECEIVABLE", counterparty="Forecast Demo Major Collection", currency="USD", amount=Decimal("18000000"), due_date=date.today()+timedelta(days=73), probability=Decimal("0.72")),
    ])
    db.commit()



def _seed_market_risk_demo(db: Session) -> None:
    if db.scalar(select(DebtPosition.id).limit(1)):
        return

    entities = db.scalars(select(LegalEntity)).all()
    e = {x.country_code: x for x in entities}
    if not all(code in e for code in ("IN", "US", "DE", "SG", "GB", "JP")):
        return

    db.add_all([
        DebtPosition(entity_id=e["US"].id, lender="JPMorgan", currency="USD", principal=Decimal("30000000"), rate_type="FLOATING", coupon_rate=Decimal("0.0525"), benchmark="SOFR", spread_bps=Decimal("145"), maturity_date=date.today()+timedelta(days=540)),
        DebtPosition(entity_id=e["DE"].id, lender="Deutsche Bank", currency="EUR", principal=Decimal("22000000"), rate_type="FIXED", coupon_rate=Decimal("0.0410"), maturity_date=date.today()+timedelta(days=760)),
        DebtPosition(entity_id=e["IN"].id, lender="State Bank of India", currency="INR", principal=Decimal("1200000000"), rate_type="FLOATING", coupon_rate=Decimal("0.0830"), benchmark="MCLR", spread_bps=Decimal("110"), maturity_date=date.today()+timedelta(days=620)),
        DebtPosition(entity_id=e["GB"].id, lender="HSBC", currency="GBP", principal=Decimal("10000000"), rate_type="FIXED", coupon_rate=Decimal("0.0475"), maturity_date=date.today()+timedelta(days=880)),
    ])

    db.add_all([
        CounterpartyLimit(counterparty="HDFC Bank", exposure_limit_reporting_ccy=Decimal("12000000"), warning_utilization=Decimal("0.80"), credit_rating="A"),
        CounterpartyLimit(counterparty="Deutsche Bank", exposure_limit_reporting_ccy=Decimal("10000000"), warning_utilization=Decimal("0.80"), credit_rating="A+"),
        CounterpartyLimit(counterparty="JPMorgan", exposure_limit_reporting_ccy=Decimal("18000000"), warning_utilization=Decimal("0.80"), credit_rating="A+"),
        CounterpartyLimit(counterparty="DBS", exposure_limit_reporting_ccy=Decimal("9000000"), warning_utilization=Decimal("0.80"), credit_rating="AA-"),
    ])

    # Additional hedges: one FX option and one pay-fixed IRS. A deliberately unmapped FX trade
    # is included to prove that the control layer catches speculative/unlinked positions.
    db.add_all([
        DerivativePosition(entity_id=e["IN"].id, instrument_type="FX_OPTION", counterparty="HDFC Bank", exposure_currency="USD", notional=Decimal("1500000"), hedge_direction="SELL", maturity_date=date.today()+timedelta(days=24), market_value_reporting_ccy=Decimal("70000"), hedge_designation="USD_RECEIVABLE_HEDGE", underlying_reference="AR-USD-PORTFOLIO"),
        DerivativePosition(entity_id=e["US"].id, instrument_type="INTEREST_RATE_SWAP", counterparty="JPMorgan", exposure_currency="USD", notional=Decimal("15000000"), hedge_direction="PAY_FIXED", maturity_date=date.today()+timedelta(days=420), market_value_reporting_ccy=Decimal("-250000"), hedge_designation="FLOATING_DEBT_HEDGE", underlying_reference="US-SOFR-DEBT"),
        DerivativePosition(entity_id=e["SG"].id, instrument_type="FX_FORWARD", counterparty="DBS", exposure_currency="JPY", notional=Decimal("180000000"), hedge_direction="BUY", maturity_date=date.today()+timedelta(days=18), market_value_reporting_ccy=Decimal("45000"), hedge_designation=None, underlying_reference=None),
    ])

    db.add_all([
        TreasuryPolicy(policy_code="FX_HEDGE_RATIO_MIN", description="Minimum hedge coverage for material forecast FX exposures", threshold_value=Decimal("0.60")),
        TreasuryPolicy(policy_code="FX_HEDGE_RATIO_MAX", description="Maximum normal hedge coverage before escalation", threshold_value=Decimal("0.90")),
        TreasuryPolicy(policy_code="MAX_FLOATING_RATE_SHARE", description="Maximum residual floating-rate debt share after hedges", threshold_value=Decimal("0.50")),
    ])
    db.commit()


def _seed_mvp4_demo(db: Session) -> None:
    if db.scalar(select(CashRestriction.id).limit(1)):
        return

    entities = db.scalars(select(LegalEntity)).all()
    e = {x.country_code: x for x in entities}
    if not all(code in e for code in ("IN", "US", "DE", "SG", "GB", "JP")):
        return

    now = datetime.now(UTC).replace(tzinfo=None)
    # Secondary USD operating/pooling accounts prove the liquidity engine handles multi-currency accounts correctly.
    db.add_all([
        BankAccount(entity_id=e["IN"].id, bank_name="Citi Pool", country_code="IN", currency="USD", book_balance=Decimal("8000000"), restricted_balance=Decimal("0"), committed_outflows=Decimal("0"), last_updated=now),
        BankAccount(entity_id=e["SG"].id, bank_name="Citi Pool", country_code="SG", currency="USD", book_balance=Decimal("6000000"), restricted_balance=Decimal("0"), committed_outflows=Decimal("0"), last_updated=now),
        BankAccount(entity_id=e["GB"].id, bank_name="Citi Pool", country_code="GB", currency="USD", book_balance=Decimal("2000000"), restricted_balance=Decimal("0"), committed_outflows=Decimal("0"), last_updated=now),
    ])

    db.add_all([
        CashRestriction(entity_id=e["IN"].id, restriction_type="TAX", currency="INR", restricted_amount=Decimal("400000000"), description="Synthetic tax-sensitive cash reserve pending local review", source_reference="SYNTHETIC_DEMO_NOT_LEGAL_ADVICE"),
        CashRestriction(entity_id=e["JP"].id, restriction_type="REGULATORY", currency="JPY", restricted_amount=Decimal("300000000"), description="Synthetic local cash mobility restriction", source_reference="SYNTHETIC_DEMO_NOT_LEGAL_ADVICE"),
        CashRestriction(entity_id=e["SG"].id, restriction_type="OPERATIONAL", currency="SGD", restricted_amount=Decimal("3000000"), description="Regional operating reserve", source_reference="SYNTHETIC_TREASURY_POLICY"),
    ])

    pool = CashPool(pool_name="Global USD Physical Pool", header_entity_id=e["US"].id, pool_type="PHYSICAL", currency="USD")
    db.add(pool)
    db.flush()
    db.add_all([
        CashPoolMember(cash_pool_id=pool.id, entity_id=e["US"].id, sweep_target_local=Decimal("20000000")),
        CashPoolMember(cash_pool_id=pool.id, entity_id=e["IN"].id, sweep_target_local=Decimal("3000000")),
        CashPoolMember(cash_pool_id=pool.id, entity_id=e["SG"].id, sweep_target_local=Decimal("2000000")),
        CashPoolMember(cash_pool_id=pool.id, entity_id=e["GB"].id, sweep_target_local=Decimal("4000000")),
    ])

    db.add_all([
        IntercompanyFacility(lender_entity_id=e["SG"].id, borrower_entity_id=e["GB"].id, currency="USD", limit_amount=Decimal("10000000"), drawn_amount=Decimal("1000000"), interest_rate=Decimal("0.052"), maturity_date=date.today()+timedelta(days=365), transfer_pricing_min_rate=Decimal("0.045"), transfer_pricing_max_rate=Decimal("0.060")),
        IntercompanyFacility(lender_entity_id=e["IN"].id, borrower_entity_id=e["GB"].id, currency="USD", limit_amount=Decimal("5000000"), drawn_amount=Decimal("0"), interest_rate=Decimal("0.065"), maturity_date=date.today()+timedelta(days=270), transfer_pricing_min_rate=Decimal("0.050"), transfer_pricing_max_rate=Decimal("0.060")),
    ])

    # Synthetic tax rules are intentionally marked REVIEW_REQUIRED and are not legal/tax advice.
    db.add_all([
        TaxRule(from_country_code="GB", to_country_code="SG", cash_flow_type="INTEREST", rate=Decimal("0.05"), source_reference="SYNTHETIC_DEMO_NOT_LEGAL_ADVICE", review_status="REVIEW_REQUIRED"),
        TaxRule(from_country_code="GB", to_country_code="IN", cash_flow_type="INTEREST", rate=Decimal("0.10"), source_reference="SYNTHETIC_DEMO_NOT_LEGAL_ADVICE", review_status="REVIEW_REQUIRED"),
    ])

    db.add_all([
        CollateralAgreement(counterparty="HDFC Bank", threshold_reporting_ccy=Decimal("250000"), minimum_transfer_amount_reporting_ccy=Decimal("100000"), independent_amount_reporting_ccy=Decimal("0"), collateral_posted_reporting_ccy=Decimal("0"), collateral_received_reporting_ccy=Decimal("100000"), eligible_collateral_currency="USD"),
        CollateralAgreement(counterparty="Deutsche Bank", threshold_reporting_ccy=Decimal("100000"), minimum_transfer_amount_reporting_ccy=Decimal("50000"), collateral_posted_reporting_ccy=Decimal("0"), collateral_received_reporting_ccy=Decimal("0"), eligible_collateral_currency="USD"),
        CollateralAgreement(counterparty="JPMorgan", threshold_reporting_ccy=Decimal("150000"), minimum_transfer_amount_reporting_ccy=Decimal("50000"), independent_amount_reporting_ccy=Decimal("100000"), collateral_posted_reporting_ccy=Decimal("100000"), collateral_received_reporting_ccy=Decimal("0"), eligible_collateral_currency="USD"),
        CollateralAgreement(counterparty="DBS", threshold_reporting_ccy=Decimal("75000"), minimum_transfer_amount_reporting_ccy=Decimal("25000"), collateral_posted_reporting_ccy=Decimal("0"), collateral_received_reporting_ccy=Decimal("0"), eligible_collateral_currency="USD"),
    ])

    debts = db.scalars(select(DebtPosition)).all()
    by_lender = {d.lender: d for d in debts}
    if "JPMorgan" in by_lender:
        db.add(CovenantTest(debt_position_id=by_lender["JPMorgan"].id, covenant_code="NET_LEVERAGE_MAX", metric_name="Net leverage", threshold_value=Decimal("3.50"), current_value=Decimal("3.28"), direction="MAX", warning_buffer_pct=Decimal("0.10"), testing_date=date.today()+timedelta(days=30)))
    if "Deutsche Bank" in by_lender:
        db.add(CovenantTest(debt_position_id=by_lender["Deutsche Bank"].id, covenant_code="INTEREST_COVER_MIN", metric_name="Interest cover", threshold_value=Decimal("3.00"), current_value=Decimal("3.18"), direction="MIN", warning_buffer_pct=Decimal("0.10"), testing_date=date.today()+timedelta(days=30)))
    if "State Bank of India" in by_lender:
        db.add(CovenantTest(debt_position_id=by_lender["State Bank of India"].id, covenant_code="DSCR_MIN", metric_name="Debt service coverage", threshold_value=Decimal("1.20"), current_value=Decimal("1.42"), direction="MIN", warning_buffer_pct=Decimal("0.10"), testing_date=date.today()+timedelta(days=60)))

    db.add_all([
        TreasuryPolicy(policy_code="MIN_TRANSFERABLE_CASH_BUFFER", description="Do not transfer cash below local minimum plus configured mobility restrictions", threshold_value=None),
        TreasuryPolicy(policy_code="COLLATERAL_LIQUIDITY_BUFFER", description="Maintain liquidity capacity for current and stressed collateral calls", threshold_value=None),
    ])
    db.commit()


def _seed_mvp5_demo(db: Session) -> None:
    if db.scalar(select(UserAccount.id).limit(1)):
        return

    now = datetime.now(UTC).replace(tzinfo=None)
    db.add_all([
        UserAccount(username="analyst1", display_name="Treasury Analyst", role="TREASURY_ANALYST"),
        UserAccount(username="manager1", display_name="Treasury Manager", role="TREASURY_MANAGER"),
        UserAccount(username="treasurer1", display_name="Group Treasurer", role="GROUP_TREASURER"),
        UserAccount(username="risk1", display_name="Market & Liquidity Risk Manager", role="RISK_MANAGER"),
        UserAccount(username="executor1", display_name="Treasury Payment Operator", role="PAYMENT_OPERATOR"),
        UserAccount(username="auditor1", display_name="Treasury Auditor", role="AUDITOR"),
    ])

    db.add_all([
        MarketDataFeed(feed_name="PRIMARY_FX_STREAM", asset_class="FX", source_type="PRIMARY", status="ACTIVE", last_received_at=now-timedelta(minutes=2), stale_after_minutes=10, required_for_execution=True),
        MarketDataFeed(feed_name="PRIMARY_RATES_STREAM", asset_class="RATES", source_type="PRIMARY", status="ACTIVE", last_received_at=now-timedelta(minutes=3), stale_after_minutes=15, required_for_execution=True),
        MarketDataFeed(feed_name="SECONDARY_FX_BACKUP", asset_class="FX", source_type="SECONDARY", status="ACTIVE", last_received_at=now-timedelta(minutes=70), stale_after_minutes=30, required_for_execution=False),
    ])

    bank = SourceConnector(connector_name="GLOBAL_BANK_API", connector_type="BANK", system_name="Multi-bank API / SWIFT Adapter", status="ACTIVE", last_success_at=now-timedelta(minutes=4), stale_after_minutes=30, required_for_execution=True, owner="TREASURY_TECH")
    erp = SourceConnector(connector_name="GLOBAL_ERP", connector_type="ERP", system_name="SAP S/4HANA Demo Adapter", status="ACTIVE", last_success_at=now-timedelta(minutes=8), stale_after_minutes=60, required_for_execution=True, owner="FINANCE_SYSTEMS")
    tax = SourceConnector(connector_name="TAX_RULE_LIBRARY", connector_type="TAX", system_name="Reviewed Tax Content", status="ACTIVE", last_success_at=now-timedelta(hours=20), stale_after_minutes=1440, required_for_execution=False, owner="GLOBAL_TAX")
    db.add_all([bank, erp, tax])
    db.flush()

    db.add_all([
        ReconciliationRun(connector_id=bank.id, run_type="BANK_TO_LEDGER", source_total=Decimal("106100000"), target_total=Decimal("106100000"), difference=Decimal("0"), unmatched_count=0, status="PASS", run_at=now-timedelta(minutes=5)),
        ReconciliationRun(connector_id=erp.id, run_type="AR_AP_TO_TREASURY", source_total=Decimal("42750000"), target_total=Decimal("42725000"), difference=Decimal("25000"), unmatched_count=2, status="WARN", run_at=now-timedelta(minutes=12)),
    ])

    trades = db.scalars(select(DerivativePosition).order_by(DerivativePosition.id)).all()
    mapped = [t for t in trades if t.underlying_reference]
    if mapped:
        db.add(HedgeAccountingDesignation(
            derivative_position_id=mapped[0].id,
            designation_type="CASH_FLOW_HEDGE",
            hedged_item_reference=mapped[0].underlying_reference or "DEMO_HEDGED_ITEM",
            risk_component=f"{mapped[0].exposure_currency}_FX_RISK",
            hedge_ratio=Decimal("1.0"),
            documentation_status="COMPLETE",
            effectiveness_status="PASS",
            designation_date=date.today()-timedelta(days=20),
            last_tested_at=now-timedelta(days=1),
        ))
    if len(mapped) > 1:
        db.add(HedgeAccountingDesignation(
            derivative_position_id=mapped[1].id,
            designation_type="CASH_FLOW_HEDGE",
            hedged_item_reference=mapped[1].underlying_reference or "DEMO_HEDGED_ITEM_2",
            risk_component=f"{mapped[1].exposure_currency}_FX_RISK",
            hedge_ratio=Decimal("0.85"),
            documentation_status="DRAFT",
            effectiveness_status="NOT_TESTED",
            designation_date=date.today()-timedelta(days=5),
            last_tested_at=None,
        ))

    db.add_all([
        ScenarioTemplate(scenario_code="COLLECTION_DELAY", label="Collections delay", receivable_multiplier=Decimal("0.75"), payable_multiplier=Decimal("1.00"), facility_availability=Decimal("0.90"), fx_shock_pct=Decimal("0.05"), rate_shock_bps=100),
        ScenarioTemplate(scenario_code="MARKET_LIQUIDITY_FREEZE", label="Market and facility liquidity freeze", receivable_multiplier=Decimal("0.85"), payable_multiplier=Decimal("1.10"), facility_availability=Decimal("0.40"), fx_shock_pct=Decimal("0.12"), rate_shock_bps=250),
        ScenarioTemplate(scenario_code="COMBINED_SEVERE", label="Combined severe treasury stress", receivable_multiplier=Decimal("0.60"), payable_multiplier=Decimal("1.25"), facility_availability=Decimal("0.25"), fx_shock_pct=Decimal("0.15"), rate_shock_bps=300),
    ])

    entities = {x.country_code: x for x in db.scalars(select(LegalEntity)).all()}
    if "US" in entities and "DE" in entities:
        db.add(TransactionProposal(
            proposal_type="CASH_TRANSFER",
            source_entity_id=entities["US"].id,
            target_entity_id=entities["DE"].id,
            currency="USD",
            amount=Decimal("5000000"),
            purpose="Pre-position liquidity for European supplier settlement",
            created_by="analyst1",
            status="PENDING_APPROVAL",
            control_status="WARNING",
            control_summary='[{"code":"DEMO_SEEDED","status":"WARN","severity":"MEDIUM","message":"Seeded proposal; rerun controls before release."}]',
            required_approvals=1,
        ))

    db.add_all([
        TreasuryPolicy(policy_code="MAKER_CHECKER_REQUIRED", description="Material treasury transactions require independent approval and release", threshold_value=None),
        TreasuryPolicy(policy_code="MARKET_DATA_STALENESS_BLOCK", description="Block hedge execution when required primary market data is stale", threshold_value=None),
        TreasuryPolicy(policy_code="RECONCILIATION_BEFORE_RELEASE", description="Block release when required reconciliation control fails", threshold_value=None),
    ])
    db.commit()


def _seed_mvp6_demo(db: Session) -> None:
    if db.scalar(select(PaymentHistory.id).limit(1)):
        return

    entities = db.scalars(select(LegalEntity)).all()
    e = {x.country_code: x for x in entities}
    if not all(code in e for code in ("IN", "US", "DE", "SG", "GB", "JP")):
        return

    # Synthetic historical customer-payment behaviour. The most recent cohort is deliberately
    # slightly worse to exercise drift monitoring without making the model unusable.
    counterparties = [
        ("US Distributor", "US", "USD", 1), ("EU Customer", "DE", "EUR", 2),
        ("Forecast Demo Major Collection", "US", "USD", 4),
    ] + [(f"Forecast Demo Customer W{i}", "US", "USD", (i % 5) + 1) for i in range(1, 14)]
    start = date.today() - timedelta(days=420)
    idx = 0
    for cycle in range(11):
        for cp, country, ccy, base_delay in counterparties:
            invoice = start + timedelta(days=idx * 2)
            terms = 30 if (idx % 4) else 45
            due = invoice + timedelta(days=terms)
            # deterministic behavioural noise; latest ~30% observations deteriorate by 4 days
            noise = ((idx * 7) % 9) - 3
            deterioration = 4 if idx > int(len(counterparties) * 11 * 0.70) else 0
            delay = max(0, base_delay + noise + deterioration)
            amount = Decimal(str(500000 + ((idx * 137000) % 6500000)))
            entity = e["DE"] if country == "DE" else e["US"]
            db.add(PaymentHistory(
                entity_id=entity.id, counterparty=cp, country_code=country, currency=ccy,
                amount=amount, invoice_date=invoice, due_date=due, paid_date=due + timedelta(days=delay),
                terms_days=terms, source_reference="SYNTHETIC_ERP_HISTORY_MVP6",
            ))
            idx += 1

    # Intraday payment history for anomaly detection plus today's liquidity queue.
    now = datetime.now(UTC).replace(tzinfo=None)
    ref = 1
    for d in range(1, 25):
        day = date.today() - timedelta(days=d)
        for j in range(4):
            scheduled = datetime.combine(day, datetime.min.time()) + timedelta(hours=9 + j * 2, minutes=(j * 11) % 50)
            payment_type = ["SUPPLIER", "CUSTOMER_RECEIPT", "INTERCOMPANY", "CRITICAL_SUPPLIER"][j]
            direction = "INFLOW" if payment_type == "CUSTOMER_RECEIPT" else "OUTFLOW"
            amount = Decimal(str(450000 + ((d * 317000 + j * 211000) % 4200000)))
            db.add(IntradayPayment(
                entity_id=e["US"].id, payment_reference=f"HIST-{ref:04d}", direction=direction,
                payment_type=payment_type, counterparty=f"Historic CP {j+1}", currency="USD", amount=amount,
                scheduled_at=scheduled, status="SETTLED", source_reference="SYNTHETIC_PAYMENT_HUB_MVP6",
            ))
            ref += 1

    today_start = datetime.combine(date.today(), datetime.min.time())
    db.add_all([
        IntradayPayment(entity_id=e["US"].id, payment_reference="TODAY-001", direction="INFLOW", payment_type="CUSTOMER_RECEIPT", counterparty="US Distributor", currency="USD", amount=Decimal("15000000"), scheduled_at=today_start+timedelta(hours=9, minutes=15), status="SCHEDULED"),
        IntradayPayment(entity_id=e["US"].id, payment_reference="TODAY-002", direction="OUTFLOW", payment_type="PAYROLL", counterparty="Global Payroll", currency="USD", amount=Decimal("12000000"), scheduled_at=today_start+timedelta(hours=10, minutes=30), status="QUEUED"),
        IntradayPayment(entity_id=e["US"].id, payment_reference="TODAY-003", direction="OUTFLOW", payment_type="DEBT_SERVICE", counterparty="JPMorgan", currency="USD", amount=Decimal("8000000"), scheduled_at=today_start+timedelta(hours=12, minutes=15), status="QUEUED"),
        IntradayPayment(entity_id=e["US"].id, payment_reference="TODAY-004", direction="OUTFLOW", payment_type="SUPPLIER", counterparty="Rare Counterparty XYZ", currency="USD", amount=Decimal("42000000"), scheduled_at=today_start+timedelta(hours=15, minutes=40), status="HELD"),
        IntradayPayment(entity_id=e["US"].id, payment_reference="TODAY-005", direction="OUTFLOW", payment_type="DISCRETIONARY", counterparty="Strategic Project Vendor", currency="USD", amount=Decimal("4000000"), scheduled_at=today_start+timedelta(hours=17, minutes=10), status="SCHEDULED"),
    ])

    # Independent values are deliberately sourced independently from the book MTM input.
    trades = db.scalars(select(DerivativePosition).where(DerivativePosition.status == "OPEN").order_by(DerivativePosition.id)).all()
    for i, trade in enumerate(trades):
        book = Decimal(trade.market_value_reporting_ccy)
        if i == len(trades) - 1:
            vals = [Decimal("390000"), Decimal("410000")]
        else:
            vals = [book + Decimal("25000"), book - Decimal("15000")]
        for source, value in zip(("INDEPENDENT_PRICER_A", "INDEPENDENT_PRICER_B"), vals):
            db.add(IndependentValuation(
                derivative_position_id=trade.id, source_name=source, source_type="INDEPENDENT",
                independent_value_reporting_ccy=value, observed_at=now-timedelta(minutes=8+i),
                valuation_method="SYNTHETIC_EXTERNAL_PRICER",
            ))

    db.add_all([
        PaymentScreeningCase(payment_reference="TODAY-002", counterparty="Global Payroll", provider="SCREENING_CONNECTOR_DEMO", status="CLEAR", screened_at=now-timedelta(minutes=3), list_version="SYNTHETIC-2026-10-03", reason="No synthetic match."),
        PaymentScreeningCase(payment_reference="TODAY-003", counterparty="JPMorgan", provider="SCREENING_CONNECTOR_DEMO", status="CLEAR", screened_at=now-timedelta(minutes=3), list_version="SYNTHETIC-2026-10-03", reason="No synthetic match."),
        PaymentScreeningCase(payment_reference="TODAY-004", counterparty="Rare Counterparty XYZ", provider="SCREENING_CONNECTOR_DEMO", status="POTENTIAL_MATCH", screened_at=now-timedelta(minutes=2), list_version="SYNTHETIC-2026-10-03", reason="Synthetic potential-name match for control testing; requires human compliance review."),
    ])
    db.commit()


def _seed_mvp7_demo(db: Session) -> None:
    if db.scalar(select(DerivativeValuationTerms.id).limit(1)):
        return

    now = datetime.now(UTC).replace(tzinfo=None)
    trades = db.scalars(select(DerivativePosition).where(DerivativePosition.status == "OPEN").order_by(DerivativePosition.id)).all()

    for trade in trades:
        if trade.instrument_type == "FX_FORWARD" and trade.counterparty == "HDFC Bank":
            db.add(DerivativeValuationTerms(derivative_position_id=trade.id, model_type="FX_FORWARD", currency_pair="USD/INR", contracted_rate=Decimal("91.50"), notional_currency="USD"))
        elif trade.instrument_type == "FX_FORWARD" and trade.counterparty == "Deutsche Bank":
            db.add(DerivativeValuationTerms(derivative_position_id=trade.id, model_type="FX_FORWARD", currency_pair="EUR/USD", contracted_rate=Decimal("1.1300"), notional_currency="EUR"))
        elif trade.instrument_type == "FX_OPTION":
            db.add(DerivativeValuationTerms(derivative_position_id=trade.id, model_type="GARMAN_KOHLHAGEN", currency_pair="USD/INR", strike=Decimal("92.00"), option_type="PUT", notional_currency="USD"))
        elif trade.instrument_type == "INTEREST_RATE_SWAP":
            db.add(DerivativeValuationTerms(derivative_position_id=trade.id, model_type="IRS_PAR_RATE", fixed_rate=Decimal("0.0450"), floating_spread_bps=Decimal("0"), payment_frequency_per_year=4, notional_currency="USD"))
        elif trade.instrument_type == "FX_FORWARD" and trade.counterparty == "DBS":
            db.add(DerivativeValuationTerms(derivative_position_id=trade.id, model_type="FX_FORWARD", currency_pair="JPY/USD", contracted_rate=Decimal("0.00672"), notional_currency="JPY"))

    curve_data = {
        "USD": [(30, "0.0520"), (90, "0.0510"), (365, "0.0480"), (730, "0.0450")],
        "INR": [(30, "0.0670"), (90, "0.0660"), (365, "0.0640"), (730, "0.0620")],
        "EUR": [(30, "0.0330"), (90, "0.0320"), (365, "0.0300"), (730, "0.0280")],
        "JPY": [(30, "0.0080"), (90, "0.0090"), (365, "0.0110"), (730, "0.0130")],
    }
    for ccy, points in curve_data.items():
        for tenor, rate in points:
            db.add(MarketCurvePoint(curve_name=f"{ccy}_OIS_DEMO", currency=ccy, curve_type="DISCOUNT", tenor_days=tenor, zero_rate=Decimal(rate), as_of=now-timedelta(minutes=4), source="SYNTHETIC_PRIMARY_CURVE"))
    for tenor, vol in [(30, "0.090"), (90, "0.100"), (365, "0.110")]:
        db.add(VolatilityQuote(asset_class="FX", underlying="USD/INR", tenor_days=tenor, quote_type="ATM", volatility=Decimal(vol), as_of=now-timedelta(minutes=5), source="SYNTHETIC_PRIMARY_VOL"))

    agreements = {x.counterparty: x for x in db.scalars(select(CollateralAgreement)).all()}
    set_specs = [
        ("NS-HDFC-01", "HDFC Bank", True, "APPROVED", "ENGLISH_LAW"),
        ("NS-DEUTSCHE-01", "Deutsche Bank", True, "APPROVED", "ENGLISH_LAW"),
        ("NS-JPM-01", "JPMorgan", True, "APPROVED", "NEW_YORK_LAW"),
        ("NS-DBS-01", "DBS", False, "REVIEW_REQUIRED", "SINGAPORE_LAW"),
    ]
    sets = {}
    for code, cp, enforceable, opinion, law in set_specs:
        ca = agreements.get(cp)
        ns = LegalNettingSet(netting_set_code=code, counterparty=cp, agreement_type="ISDA_MASTER", governing_law=law, close_out_netting_enforceable=enforceable, legal_opinion_status=opinion, collateral_agreement_id=ca.id if ca else None, last_legal_review_date=date.today()-timedelta(days=90 if opinion == "APPROVED" else 400))
        db.add(ns); db.flush(); sets[cp] = ns
    for trade in trades:
        if trade.counterparty in sets:
            db.add(NettingSetTrade(netting_set_id=sets[trade.counterparty].id, derivative_position_id=trade.id))

    db.add_all([
        ModelDeployment(model_code="PAYMENT_BEHAVIOUR_RF", version="1.0.0", deployment_role="CHAMPION", approval_status="APPROVED", approved_by="MODEL_RISK_COMMITTEE", promotion_threshold_pct=Decimal("0.05"), notes="Current production champion."),
        ModelDeployment(model_code="PAYMENT_BEHAVIOUR_RF", version="GB_1.0.0", deployment_role="CHALLENGER", approval_status="SHADOW", approved_by="MODEL_RISK_COMMITTEE", promotion_threshold_pct=Decimal("0.05"), notes="Shadow challenger; cannot auto-promote."),
    ])

    db.add_all([
        ResilienceControl(component_name="Treasury API", criticality_tier="TIER_1", rto_minutes=30, rpo_minutes=5, multi_region=True, last_dr_test_at=now-timedelta(days=45), last_dr_test_result="PASS", owner="TREASURY_TECH"),
        ResilienceControl(component_name="Market Data Gateway", criticality_tier="TIER_1", rto_minutes=15, rpo_minutes=2, multi_region=True, last_dr_test_at=now-timedelta(days=60), last_dr_test_result="PASS", owner="MARKET_DATA_PLATFORM"),
        ResilienceControl(component_name="Payment Release Service", criticality_tier="TIER_1", rto_minutes=30, rpo_minutes=5, multi_region=False, last_dr_test_at=now-timedelta(days=220), last_dr_test_result="WARN", owner="TREASURY_OPERATIONS"),
        ResilienceControl(component_name="ML Forecast Service", criticality_tier="TIER_2", rto_minutes=240, rpo_minutes=60, multi_region=False, last_dr_test_at=now-timedelta(days=100), last_dr_test_result="PASS", owner="TREASURY_MODEL_RISK"),
    ])
    db.commit()

def _seed_mvp8_demo(db: Session) -> None:
    if db.scalar(select(TreasuryEvent.id).limit(1)):
        return

    now = datetime.now(UTC).replace(tzinfo=None)
    market_connector = db.scalar(select(SourceConnector).where(SourceConnector.connector_name == "MARKET_DATA_GATEWAY"))
    if market_connector is None:
        market_connector = SourceConnector(
            connector_name="MARKET_DATA_GATEWAY", connector_type="MARKET", system_name="Approved Market Data Gateway",
            status="ACTIVE", last_success_at=now-timedelta(minutes=2), stale_after_minutes=15,
            required_for_execution=False, owner="MARKET_DATA_PLATFORM",
        )
        db.add(market_connector)

    seed_events = [
        ("MVP8-BANK-0001", "BANK_BALANCE", "GLOBAL_BANK_API", "MULTI_BANK_API", now-timedelta(minutes=2), 1001, {"snapshot": "baseline"}),
        ("MVP8-ERP-0001", "ERP_CASH_FLOW", "GLOBAL_ERP", "SAP_S4", now-timedelta(minutes=5), 2201, {"snapshot": "baseline"}),
        ("MVP8-MKT-0001", "MARKET_FX_QUOTE", "MARKET_DATA_GATEWAY", "MARKET_DATA_PLATFORM", now-timedelta(minutes=1), 9001, {"snapshot": "baseline"}),
    ]
    import hashlib, json
    for key, event_type, connector, source, event_time, sequence_no, payload in seed_events:
        payload_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        payload_hash = hashlib.sha256(payload_json.encode()).hexdigest()
        db.add(TreasuryEvent(
            idempotency_key=key, event_type=event_type, source_system=source, connector_name=connector,
            sequence_no=sequence_no, schema_version="1.0", event_time=event_time, received_at=event_time+timedelta(seconds=3),
            payload_hash=payload_hash, payload_json=payload_json, processing_status="APPLIED",
        ))
        db.add(ConnectorCheckpoint(
            connector_name=connector, source_system=source, last_sequence_no=sequence_no,
            last_event_time=event_time, last_received_at=event_time+timedelta(seconds=3), accepted_count=1, status="ACTIVE",
        ))
    db.commit()



def _seed_mvp11_demo(db: Session) -> None:
    if db.scalar(select(MarketReturnObservation.id).limit(1)):
        return

    import math
    factors = {
        "INR": (0.00015, 0.0045, 0.55),
        "EUR": (-0.00002, 0.0060, 0.70),
        "GBP": (0.00001, 0.0065, 0.65),
        "JPY": (-0.00005, 0.0070, -0.25),
        "SGD": (0.00003, 0.0035, 0.50),
    }
    start = date.today() - timedelta(days=220)
    business_day = 0
    for i in range(220):
        d = start + timedelta(days=i)
        if d.weekday() >= 5:
            continue
        common = 0.0040 * math.sin((business_day + 1) * 0.37) + 0.0020 * math.cos((business_day + 1) * 0.11)
        for j, (factor, (drift, idio_scale, beta)) in enumerate(factors.items()):
            idio = idio_scale * math.sin((business_day + 1) * (0.19 + j * 0.031) + j * 0.7)
            ret = drift + beta * common + idio
            db.add(MarketReturnObservation(
                observation_date=d, factor_type="FX", factor_key=factor, return_value=Decimal(str(round(ret, 10))),
                source="SYNTHETIC_GOVERNED_HISTORY", approved=True,
            ))
        business_day += 1

    db.add_all([
        CounterpartyCreditMetric(counterparty="HDFC Bank", one_year_pd=Decimal("0.0060"), lgd=Decimal("0.55"), funding_spread_bps=Decimal("85"), source="SYNTHETIC_APPROVED_CREDIT_CURVE", approved=True),
        CounterpartyCreditMetric(counterparty="Deutsche Bank", one_year_pd=Decimal("0.0045"), lgd=Decimal("0.55"), funding_spread_bps=Decimal("70"), source="SYNTHETIC_APPROVED_CREDIT_CURVE", approved=True),
        CounterpartyCreditMetric(counterparty="JPMorgan", one_year_pd=Decimal("0.0030"), lgd=Decimal("0.50"), funding_spread_bps=Decimal("60"), source="SYNTHETIC_APPROVED_CREDIT_CURVE", approved=True),
        CounterpartyCreditMetric(counterparty="DBS", one_year_pd=Decimal("0.0025"), lgd=Decimal("0.50"), funding_spread_bps=Decimal("55"), source="SYNTHETIC_APPROVED_CREDIT_CURVE", approved=True),
    ])

    db.add_all([
        TreasuryRiskLimit(limit_code="LIM_BUFFER_BREACH_PROB", category="LIQUIDITY", metric_name="BUFFER_BREACH_PROBABILITY", comparator="MAX", threshold_value=Decimal("0.10"), warning_utilization=Decimal("0.75")),
        TreasuryRiskLimit(limit_code="LIM_SURVIVAL_DAYS", category="LIQUIDITY", metric_name="SURVIVAL_HORIZON_DAYS", comparator="MIN", threshold_value=Decimal("56"), warning_utilization=Decimal("1.25")),
        TreasuryRiskLimit(limit_code="LIM_FX_VAR_10D", category="MARKET", metric_name="FX_VAR_95_10D", comparator="MAX", threshold_value=Decimal("1500000"), warning_utilization=Decimal("0.75"), currency="USD"),
        TreasuryRiskLimit(limit_code="LIM_TOP_LENDER", category="FUNDING", metric_name="TOP_LENDER_SHARE", comparator="MAX", threshold_value=Decimal("0.45"), warning_utilization=Decimal("0.80")),
        TreasuryRiskLimit(limit_code="LIM_CP_UTIL", category="COUNTERPARTY", metric_name="MAX_COUNTERPARTY_UTILIZATION", comparator="MAX", threshold_value=Decimal("0.90"), warning_utilization=Decimal("0.80")),
    ])
    db.commit()


def _seed_mvp14_demo(db: Session) -> None:
    if db.scalar(select(ForecastPerformanceRecord.id).limit(1)):
        return

    entities = db.scalars(select(LegalEntity)).all()
    e = {x.country_code: x for x in entities}
    if not all(code in e for code in ("IN", "US", "DE")):
        return

    configs = {
        "US": ("USD", Decimal("9000000"), Decimal("6500000")),
        "DE": ("EUR", Decimal("6200000"), Decimal("4400000")),
        "IN": ("INR", Decimal("520000000"), Decimal("380000000")),
    }

    # Historical forecast-vs-actual observations. The demo includes a mild optimistic
    # cash bias: collections tend to land below forecast while payables slightly exceed plan.
    for week_back in range(1, 17):
        target = date.today() - timedelta(days=week_back * 7)
        for idx, code in enumerate(("US", "DE", "IN")):
            ccy, inflow_base, outflow_base = configs[code]
            horizon = (7, 30, 60)[(week_back + idx) % 3]
            forecast_date = target - timedelta(days=horizon)
            scale = Decimal("1") + Decimal((week_back + idx) % 5) / Decimal("20")
            inflow_forecast = inflow_base * scale
            inflow_actual_factor = Decimal("0.88") + Decimal((week_back * 3 + idx) % 8) / Decimal("100")
            outflow_forecast = outflow_base * scale
            outflow_actual_factor = Decimal("1.02") + Decimal((week_back * 5 + idx) % 7) / Decimal("100")
            db.add_all([
                ForecastPerformanceRecord(
                    entity_id=e[code].id, forecast_date=forecast_date, target_date=target, flow_type="RECEIVABLE",
                    counterparty=f"{code} Historical Customer {week_back % 5 + 1}", currency=ccy,
                    forecast_amount=inflow_forecast, actual_amount=inflow_forecast * inflow_actual_factor,
                    model_code="TREASURY_CASH_FORECAST_V1", horizon_days=horizon,
                    source_reference="SYNTHETIC_FORECAST_HISTORY_MVP14",
                ),
                ForecastPerformanceRecord(
                    entity_id=e[code].id, forecast_date=forecast_date, target_date=target, flow_type="PAYABLE",
                    counterparty=f"{code} Historical Supplier {week_back % 4 + 1}", currency=ccy,
                    forecast_amount=outflow_forecast, actual_amount=outflow_forecast * outflow_actual_factor,
                    model_code="TREASURY_CASH_FORECAST_V1", horizon_days=horizon,
                    source_reference="SYNTHETIC_FORECAST_HISTORY_MVP14",
                ),
            ])

    # Monthly balance-sheet observations support true working-capital cycle metrics.
    wc_configs = {
        "US": ("USD", Decimal("42000000"), Decimal("25000000"), 43, 39, 34),
        "DE": ("EUR", Decimal("26000000"), Decimal("16000000"), 46, 42, 38),
        "IN": ("INR", Decimal("2100000000"), Decimal("1280000000"), 49, 45, 41),
    }
    for month_back in range(12, 0, -1):
        period_end = date.today() - timedelta(days=month_back * 30)
        for idx, (code, (ccy, revenue_base, cogs_base, dso_base, dpo_base, dio_base)) in enumerate(wc_configs.items()):
            growth = Decimal("0.92") + Decimal(12 - month_back) * Decimal("0.009") + Decimal(idx) * Decimal("0.005")
            revenue = revenue_base * growth
            cogs = cogs_base * growth
            # Receivable days deteriorate slightly in the latest months; payables stay relatively stable.
            dso = Decimal(dso_base + max(0, 7 - month_back) // 2)
            dpo = Decimal(dpo_base + ((month_back + idx) % 3) - 1)
            dio = Decimal(dio_base + ((month_back * 2 + idx) % 4) - 1)
            db.add(WorkingCapitalObservation(
                entity_id=e[code].id, period_end=period_end, currency=ccy, revenue=revenue, cogs=cogs,
                receivables_balance=(revenue / Decimal("30")) * dso,
                payables_balance=(cogs / Decimal("30")) * dpo,
                inventory_balance=(cogs / Decimal("30")) * dio,
                source_reference="SYNTHETIC_WORKING_CAPITAL_MVP14",
            ))

    # Open overdue receivables exercise the collection-risk and aging engine without
    # changing the forward 13-week forecast, which only includes future due dates.
    db.add_all([
        CashFlow(entity_id=e["US"].id, flow_type="RECEIVABLE", counterparty="Overdue US Retailer", currency="USD", amount=Decimal("4200000"), due_date=date.today()-timedelta(days=18), probability=Decimal("0.65"), source_reference="MVP14_OVERDUE_AR"),
        CashFlow(entity_id=e["DE"].id, flow_type="RECEIVABLE", counterparty="Overdue EU Distributor", currency="EUR", amount=Decimal("3100000"), due_date=date.today()-timedelta(days=47), probability=Decimal("0.55"), source_reference="MVP14_OVERDUE_AR"),
        CashFlow(entity_id=e["IN"].id, flow_type="RECEIVABLE", counterparty="Overdue India Channel", currency="INR", amount=Decimal("165000000"), due_date=date.today()-timedelta(days=76), probability=Decimal("0.45"), source_reference="MVP14_OVERDUE_AR"),
    ])
    db.commit()


def _seed_mvp15_20_demo(db: Session) -> None:
    if db.scalar(select(CrossBorderConstraint.id).limit(1)):
        return
    entities = db.scalars(select(LegalEntity)).all()
    e = {x.country_code: x for x in entities}
    now = datetime.now(UTC).replace(tzinfo=None)

    db.add_all([
        CrossBorderConstraint(source_country="SG", target_country="IN", transfer_type="IC_LOAN", currency="USD", max_amount_reporting=Decimal("8000000"), withholding_tax_rate=Decimal("0.10"), regulatory_status="APPROVED", legal_status="APPROVED", requires_tax_review=False, requires_legal_review=False, source_reference="SYNTHETIC_MVP15_APPROVED"),
        CrossBorderConstraint(source_country="US", target_country="DE", transfer_type="IC_LOAN", currency="USD", max_amount_reporting=Decimal("12000000"), withholding_tax_rate=Decimal("0.05"), regulatory_status="REVIEW_REQUIRED", legal_status="APPROVED", requires_tax_review=True, requires_legal_review=False, source_reference="SYNTHETIC_MVP15_REVIEW"),
        CrossBorderConstraint(source_country="US", target_country="GB", transfer_type="CASH_SWEEP", currency="USD", max_amount_reporting=Decimal("5000000"), withholding_tax_rate=Decimal("0"), regulatory_status="APPROVED", legal_status="REVIEW_REQUIRED", requires_tax_review=False, requires_legal_review=True, source_reference="SYNTHETIC_MVP15_REVIEW"),
        CrossBorderConstraint(source_country="SG", target_country="GB", transfer_type="CASH_SWEEP", currency="USD", max_amount_reporting=Decimal("5000000"), withholding_tax_rate=Decimal("0"), regulatory_status="APPROVED", legal_status="APPROVED", requires_tax_review=False, requires_legal_review=False, source_reference="SYNTHETIC_MVP15_APPROVED"),
        CrossBorderConstraint(source_country="DE", target_country="US", transfer_type="DIVIDEND", currency="EUR", max_amount_reporting=Decimal("4000000"), withholding_tax_rate=Decimal("0.05"), regulatory_status="APPROVED", legal_status="APPROVED", requires_tax_review=True, requires_legal_review=False, source_reference="SYNTHETIC_MVP15_TAX_REVIEW"),
    ])

    db.add_all([
        EnterpriseConnectorProfile(connector_code="BANK_US_JPM", connector_type="BANK", system_name="JPMorgan API", protocol="REST", auth_mode="MTLS_OAUTH", environment="UAT", status="HEALTHY", last_success_at=now-timedelta(minutes=2), latency_ms=Decimal("185"), error_rate=Decimal("0.002"), supports_idempotency=True, supports_reconciliation=True, data_contract_version="1.0"),
        EnterpriseConnectorProfile(connector_code="ERP_GLOBAL", connector_type="ERP", system_name="Global ERP", protocol="EVENT_API", auth_mode="WORKLOAD_IDENTITY", environment="UAT", status="HEALTHY", last_success_at=now-timedelta(minutes=4), latency_ms=Decimal("420"), error_rate=Decimal("0.004"), supports_idempotency=True, supports_reconciliation=True, data_contract_version="1.0"),
        EnterpriseConnectorProfile(connector_code="MARKET_PRIMARY", connector_type="MARKET", system_name="Primary Market Data", protocol="STREAM", auth_mode="CERTIFICATE", environment="UAT", status="DEGRADED", last_success_at=now-timedelta(minutes=18), latency_ms=Decimal("950"), error_rate=Decimal("0.025"), supports_idempotency=True, supports_reconciliation=False, data_contract_version="1.0"),
        EnterpriseConnectorProfile(connector_code="TMS_EXECUTION", connector_type="TMS", system_name="Treasury Execution Gateway", protocol="API", auth_mode="MTLS_OAUTH", environment="UAT", status="CONFIGURED", last_success_at=None, latency_ms=None, error_rate=Decimal("0"), supports_idempotency=True, supports_reconciliation=True, data_contract_version="1.0"),
        EnterpriseConnectorProfile(connector_code="TAX_RULES", connector_type="TAX", system_name="Tax Rules Provider", protocol="API", auth_mode="OAUTH", environment="UAT", status="HEALTHY", last_success_at=now-timedelta(minutes=6), latency_ms=Decimal("310"), error_rate=Decimal("0.003"), supports_idempotency=True, supports_reconciliation=False, data_contract_version="1.0"),
    ])

    db.add_all([
        SecurityControlRecord(control_code="SSO_MFA", domain="IDENTITY", status="PASS", evidence="OIDC + MFA architecture validated in UAT", owner="IAM", last_tested_at=now-timedelta(days=7)),
        SecurityControlRecord(control_code="SECRETS_HSM", domain="KEY_MANAGEMENT", status="WATCH", evidence="Managed secret store designed; HSM-backed execution signing pending provider integration", owner="SECURITY", last_tested_at=now-timedelta(days=3)),
        SecurityControlRecord(control_code="SIEM_EXPORT", domain="MONITORING", status="PASS", evidence="Security and audit events mapped to SIEM contract", owner="SOC", last_tested_at=now-timedelta(days=5)),
        SecurityControlRecord(control_code="ENV_SEGREGATION", domain="PLATFORM", status="PASS", evidence="Dev/UAT/Prod configuration boundary defined", owner="PLATFORM", last_tested_at=now-timedelta(days=4)),
        SecurityControlRecord(control_code="PEN_TEST", domain="APPLICATION_SECURITY", status="NOT_TESTED", evidence="Independent penetration test pending live deployment environment", owner="SECURITY", last_tested_at=None),
        SecurityControlRecord(control_code="BREAK_GLASS", domain="IDENTITY", status="PASS", evidence="Emergency access requires independent approval and audit", owner="IAM", last_tested_at=now-timedelta(days=10)),
    ])

    models = db.scalars(select(ModelRegistryEntry)).all()
    existing_model_codes = {m.model_code for m in models}
    model_rows = []
    if "TREASURY_CASH_FORECAST_V1" not in existing_model_codes:
        model_rows.append(ModelRegistryEntry(model_code="TREASURY_CASH_FORECAST_V1", version="1.0.0", model_type="CASH_FORECAST", training_rows=520, validation_status="VALIDATED", metrics_json='{"wape":0.073}', feature_schema='["entity","currency","due_date","counterparty"]', data_fingerprint="SYNTHETIC", owner="TREASURY_MODEL_RISK"))
    if "PAYMENT_BEHAVIOR_RF" not in existing_model_codes:
        model_rows.append(ModelRegistryEntry(model_code="PAYMENT_BEHAVIOR_RF", version="1.0.0", model_type="PAYMENT_BEHAVIOR", training_rows=420, validation_status="VALIDATED", metrics_json='{"delay_mae_days":3.2}', feature_schema='["counterparty","terms_days","amount","country"]', data_fingerprint="SYNTHETIC", owner="TREASURY_MODEL_RISK"))
    if "DERIVATIVE_PRICING" not in existing_model_codes:
        model_rows.append(ModelRegistryEntry(model_code="DERIVATIVE_PRICING", version="1.0.0", model_type="VALUATION", training_rows=0, validation_status="REVIEW_REQUIRED", metrics_json='{"ipv_exception_rate":0.08}', feature_schema='["curve","volatility","trade_terms"]', data_fingerprint="SYNTHETIC", owner="VALUATION_CONTROL"))
    if model_rows:
        db.add_all(model_rows)
        db.flush()
    db.add_all([
        ModelValidationRecord(model_code="TREASURY_CASH_FORECAST_V1", validation_type="BACKTEST", metric_name="WAPE", metric_value=Decimal("0.073"), threshold_value=Decimal("0.15"), comparison="LE", status="PASS", window_start=date.today()-timedelta(days=180), window_end=date.today(), notes="Synthetic historical backtest"),
        ModelValidationRecord(model_code="PAYMENT_BEHAVIOR_RF", validation_type="BACKTEST", metric_name="DELAY_MAE_DAYS", metric_value=Decimal("3.2"), threshold_value=Decimal("5.0"), comparison="LE", status="PASS", window_start=date.today()-timedelta(days=180), window_end=date.today(), notes="Synthetic holdout validation"),
        ModelValidationRecord(model_code="DERIVATIVE_PRICING", validation_type="BENCHMARK", metric_name="IPV_EXCEPTION_RATE", metric_value=Decimal("0.08"), threshold_value=Decimal("0.05"), comparison="LE", status="WATCH", window_start=date.today()-timedelta(days=30), window_end=date.today(), notes="Independent valuation exceptions require calibration review"),
    ])

    db.add_all([
        InvestigationCase(case_type="LIQUIDITY", severity="HIGH", status="OPEN", owner_role="GROUP_TREASURER", entity_id=e.get("DE").id if e.get("DE") else None, reference="CASE-LIQ-001", title="Near-term liquidity pressure", details="Review local liquidity buffer, expiring facility and approved transfer routes."),
        InvestigationCase(case_type="MARKET_DATA", severity="MEDIUM", status="OPEN", owner_role="TREASURY_OPERATIONS", reference="CASE-DATA-001", title="Primary market feed degraded", details="Validate fallback feed and restore primary market-data freshness."),
        InvestigationCase(case_type="MODEL_RISK", severity="MEDIUM", status="OPEN", owner_role="RISK", reference="CASE-MODEL-001", title="Derivative IPV exceptions", details="Review pricing inputs and independent valuation tolerances."),
        InvestigationCase(case_type="CROSS_BORDER", severity="MEDIUM", status="OPEN", owner_role="TAX", reference="CASE-TAX-001", title="Cross-border funding route requires review", details="Validate withholding tax, transfer pricing and local regulatory constraints."),
        InvestigationCase(case_type="CONTROL", severity="LOW", status="OPEN", owner_role="AUDIT", reference="CASE-AUDIT-001", title="Production evidence pack incomplete", details="Collect penetration-test, DR exercise and provider certification evidence."),
    ])

    db.add_all([
        DeploymentReadinessControl(control_code="DB_POSTGRES_HA", category="DATA", status="PASS", evidence="PostgreSQL-ready persistence and migration chain implemented", owner="PLATFORM"),
        DeploymentReadinessControl(control_code="OIDC_MFA", category="SECURITY", status="PASS", evidence="Production OIDC/JWT boundary implemented", owner="IAM"),
        DeploymentReadinessControl(control_code="HSM_EXECUTION_KEYS", category="SECURITY", status="BLOCKED", evidence="Requires deployment-specific HSM/KMS integration", owner="SECURITY"),
        DeploymentReadinessControl(control_code="BANK_CONNECTOR_CERT", category="INTEGRATION", status="BLOCKED", evidence="Real bank provider certification not executed in synthetic environment", owner="TREASURY_TECH"),
        DeploymentReadinessControl(control_code="ERP_RECON_UAT", category="INTEGRATION", status="WATCH", evidence="Contract and reconciliation logic implemented; live ERP UAT pending", owner="TREASURY_TECH"),
        DeploymentReadinessControl(control_code="MARKET_DATA_LICENSE", category="MARKET_DATA", status="BLOCKED", evidence="Production vendor entitlement/licensing required", owner="MARKET_DATA"),
        DeploymentReadinessControl(control_code="MODEL_INDEPENDENT_VALIDATION", category="MODEL_RISK", status="WATCH", evidence="Framework implemented; production models require independent validation", owner="MODEL_RISK"),
        DeploymentReadinessControl(control_code="TAX_LEGAL_SIGNOFF", category="LEGAL_TAX", status="BLOCKED", evidence="Country-specific production sign-off required", owner="TAX_LEGAL"),
        DeploymentReadinessControl(control_code="LOAD_TEST", category="RELIABILITY", status="WATCH", evidence="Load-test harness defined; production infrastructure not provisioned", owner="PLATFORM"),
        DeploymentReadinessControl(control_code="FRONTEND_LOCKFILE", category="RELEASE", status="BLOCKED", evidence="Frontend package-lock generation requires dependency resolution in the deployment/build environment", owner="PLATFORM"),
        DeploymentReadinessControl(control_code="DR_EXERCISE", category="RESILIENCE", status="BLOCKED", evidence="RTO/RPO controls defined; full failover exercise pending", owner="BCP"),
        DeploymentReadinessControl(control_code="OBSERVABILITY", category="RELIABILITY", status="PASS", evidence="Health, readiness, metrics and request IDs implemented", owner="SRE"),
        DeploymentReadinessControl(control_code="AUDIT_TRAIL", category="GOVERNANCE", status="PASS", evidence="Immutable audit/event boundaries and maker-checker controls implemented", owner="INTERNAL_CONTROL"),
    ])
    db.commit()


def _seed_production_phase1_demo(db: Session) -> None:
    existing_certification = db.scalar(select(IntegrationCertificationControl.id).limit(1)) is not None
    if existing_certification:
        now = datetime.now(UTC).replace(tzinfo=None)
        extra_controls = [
            ("SWIFT_ISO20022", "PARALLEL_RUN", "NOT_TESTED", "Requires representative shadow-period comparison before BANK_BALANCE can become authoritative"),
            ("SWIFT_ISO20022", "DATA_QUALITY_SLA", "NOT_TESTED", "Requires sustained timeliness/completeness/validity/uniqueness/reconciliation SLA evidence"),
            ("SAP_S4_FINANCE", "PARALLEL_RUN", "NOT_TESTED", "Requires representative shadow-period comparison before ERP_CASH_FLOW can become authoritative"),
            ("SAP_S4_FINANCE", "DATA_QUALITY_SLA", "NOT_TESTED", "Requires sustained data-quality SLA evidence"),
            ("ORACLE_FUSION_FIN", "PARALLEL_RUN", "NOT_TESTED", "Requires representative shadow-period comparison before ERP_CASH_FLOW can become authoritative"),
            ("ORACLE_FUSION_FIN", "DATA_QUALITY_SLA", "NOT_TESTED", "Requires sustained data-quality SLA evidence"),
            ("MARKET_DATA_LIVE", "PARALLEL_RUN", "NOT_TESTED", "Requires shadow comparison against incumbent market source before authority promotion"),
            ("MARKET_DATA_LIVE", "DATA_QUALITY_SLA", "NOT_TESTED", "Requires sustained freshness/completeness/validity SLA evidence"),
        ]
        for connector, control, status, evidence in extra_controls:
            exists = db.scalar(select(IntegrationCertificationControl.id).where(
                IntegrationCertificationControl.connector_code == connector,
                IntegrationCertificationControl.control_code == control,
            ).limit(1))
            if exists is None:
                db.add(IntegrationCertificationControl(
                    connector_code=connector, control_code=control, required=True, status=status, evidence=evidence,
                    owner="TREASURY_TECH" if connector != "MARKET_DATA_LIVE" else "MARKET_DATA",
                ))
        authority_rows = [
            ("SWIFT_ISO20022", "BANK_BALANCE"),
            ("SAP_S4_FINANCE", "ERP_CASH_FLOW"),
            ("ORACLE_FUSION_FIN", "ERP_CASH_FLOW"),
            ("MARKET_DATA_LIVE", "MARKET_QUOTE"),
            ("MARKET_DATA_LIVE", "CURVE_POINT"),
            ("MARKET_DATA_LIVE", "VOLATILITY_QUOTE"),
        ]
        for connector, domain in authority_rows:
            exists = db.scalar(select(SourceAuthorityPolicy.id).where(
                SourceAuthorityPolicy.connector_code == connector, SourceAuthorityPolicy.data_domain == domain,
            ).limit(1))
            if exists is None:
                db.add(SourceAuthorityPolicy(
                    connector_code=connector, data_domain=domain, mode="SHADOW",
                    evidence="Default Phase-1 posture: compare and certify before authoritative promotion.", updated_at=now,
                ))
        db.commit()
        return
    entities = db.scalars(select(LegalEntity)).all()
    accounts = db.scalars(select(BankAccount)).all()
    by_country = {e.country_code: e for e in entities}
    account_by_country = {a.country_code: a for a in accounts}
    now = datetime.now(UTC).replace(tzinfo=None)

    profiles = [
        ("SWIFT_ISO20022", "BANK", "SWIFT / ISO 20022 Cash Reporting", "ISO20022_XML", "MTLS_CERT"),
        ("SAP_S4_FINANCE", "ERP", "SAP S/4HANA Finance", "ODATA", "OAUTH_WORKLOAD_IDENTITY"),
        ("ORACLE_FUSION_FIN", "ERP", "Oracle Fusion Cloud Financials", "REST", "OAUTH_WORKLOAD_IDENTITY"),
        ("MARKET_DATA_LIVE", "MARKET", "Licensed Market Data Provider", "REST_STREAM", "OAUTH_CERT"),
    ]
    existing = {x.connector_code for x in db.scalars(select(EnterpriseConnectorProfile)).all()}
    for code, typ, name, protocol, auth in profiles:
        if code not in existing:
            db.add(EnterpriseConnectorProfile(
                connector_code=code, connector_type=typ, system_name=name, protocol=protocol, auth_mode=auth,
                environment="UAT", status="CONFIGURED", last_success_at=None, latency_ms=None, error_rate=Decimal("0"),
                supports_idempotency=True, supports_reconciliation=True, data_contract_version="1.0",
            ))

    for country, account in account_by_country.items():
        db.add(ExternalReferenceMap(
            connector_code="SWIFT_ISO20022", object_type="BANK_ACCOUNT", external_id=f"DEMO-{country}-001",
            internal_id=account.id, internal_code=str(account.id), source_reference="PHASE1_DEMO_MAPPING",
        ))
    company_codes = {"IN":"IN01","US":"US01","DE":"DE01","SG":"SG01","GB":"GB01","JP":"JP01"}
    for country, company_code in company_codes.items():
        entity = by_country.get(country)
        if not entity:
            continue
        for connector in ("SAP_S4_FINANCE", "ORACLE_FUSION_FIN"):
            db.add(ExternalReferenceMap(
                connector_code=connector, object_type="LEGAL_ENTITY", external_id=company_code,
                internal_id=entity.id, internal_code=country, source_reference="PHASE1_DEMO_MAPPING",
            ))

    cert_rows = [
        ("SWIFT_ISO20022", "SCHEMA_PARSE_CAMT_052_053", "PASS", "camt.052/camt.053 parser and quarantine controls covered by automated tests"),
        ("SWIFT_ISO20022", "IDEMPOTENCY", "PASS", "Source-record idempotency and collision quarantine implemented"),
        ("SWIFT_ISO20022", "BANK_PROVIDER_UAT", "NOT_TESTED", "Requires real bank/SWIFT UAT endpoint and certificates"),
        ("SWIFT_ISO20022", "VOLUME_FAILOVER_TEST", "NOT_TESTED", "Requires provider/UAT volume and failover exercise"),
        ("SWIFT_ISO20022", "CBPR_PLUS_2026_ADDRESS_READINESS", "NOT_TESTED", "Payment-instruction integration must be validated for the November 2026 CBPR+ structured/hybrid postal-address requirement"),
        ("SAP_S4_FINANCE", "CANONICAL_MAPPING", "PASS", "SAP OData adapter and company-code mapping boundary implemented"),
        ("SAP_S4_FINANCE", "ERP_RECONCILIATION", "PASS", "Bank-to-ERP detailed reconciliation engine implemented"),
        ("SAP_S4_FINANCE", "SAP_UAT_AUTH", "NOT_TESTED", "Requires real S/4HANA communication arrangement and workload identity"),
        ("ORACLE_FUSION_FIN", "CANONICAL_MAPPING", "PASS", "Oracle Fusion AR/AP REST adapter boundary implemented"),
        ("ORACLE_FUSION_FIN", "ORACLE_UAT_AUTH", "NOT_TESTED", "Requires Oracle Fusion UAT OAuth/service account"),
        ("MARKET_DATA_LIVE", "CANONICAL_MARKET_MAPPING", "PASS", "FX, curve and volatility canonical ingestion implemented"),
        ("MARKET_DATA_LIVE", "LICENSE_ENTITLEMENT", "NOT_TESTED", "Requires licensed production market-data entitlement"),
        ("MARKET_DATA_LIVE", "PRIMARY_SECONDARY_FAILOVER", "NOT_TESTED", "Requires two real provider feeds for failover certification"),
        ("SWIFT_ISO20022", "PARALLEL_RUN", "NOT_TESTED", "Requires representative shadow-period comparison before BANK_BALANCE can become authoritative"),
        ("SWIFT_ISO20022", "DATA_QUALITY_SLA", "NOT_TESTED", "Requires sustained timeliness/completeness/validity/uniqueness/reconciliation SLA evidence"),
        ("SAP_S4_FINANCE", "PARALLEL_RUN", "NOT_TESTED", "Requires representative shadow-period comparison before ERP_CASH_FLOW can become authoritative"),
        ("SAP_S4_FINANCE", "DATA_QUALITY_SLA", "NOT_TESTED", "Requires sustained data-quality SLA evidence"),
        ("ORACLE_FUSION_FIN", "PARALLEL_RUN", "NOT_TESTED", "Requires representative shadow-period comparison before ERP_CASH_FLOW can become authoritative"),
        ("ORACLE_FUSION_FIN", "DATA_QUALITY_SLA", "NOT_TESTED", "Requires sustained data-quality SLA evidence"),
        ("MARKET_DATA_LIVE", "PARALLEL_RUN", "NOT_TESTED", "Requires shadow comparison against incumbent market source before authority promotion"),
        ("MARKET_DATA_LIVE", "DATA_QUALITY_SLA", "NOT_TESTED", "Requires sustained freshness/completeness/validity SLA evidence"),
    ]
    for connector, control, status, evidence in cert_rows:
        db.add(IntegrationCertificationControl(
            connector_code=connector, control_code=control, required=True, status=status, evidence=evidence,
            owner="TREASURY_TECH" if connector != "MARKET_DATA_LIVE" else "MARKET_DATA",
            last_checked_at=now if status == "PASS" else None,
        ))

    # Real provider feeds start in SHADOW mode. Promotion to ACTIVE is a governed action
    # after connector certification, data-quality SLA evidence and parallel-run validation.
    authority_rows = [
        ("SWIFT_ISO20022", "BANK_BALANCE"),
        ("SAP_S4_FINANCE", "ERP_CASH_FLOW"),
        ("ORACLE_FUSION_FIN", "ERP_CASH_FLOW"),
        ("MARKET_DATA_LIVE", "MARKET_QUOTE"),
        ("MARKET_DATA_LIVE", "CURVE_POINT"),
        ("MARKET_DATA_LIVE", "VOLATILITY_QUOTE"),
    ]
    for connector, domain in authority_rows:
        db.add(SourceAuthorityPolicy(
            connector_code=connector, data_domain=domain, mode="SHADOW",
            evidence="Default Phase-1 posture: compare and certify before authoritative promotion.",
            updated_at=now,
        ))
    db.commit()

def seed_demo(db: Session) -> None:
    if db.scalar(select(LegalEntity.id).limit(1)):
        _seed_forecast_demo(db)
        _seed_market_risk_demo(db)
        _seed_mvp4_demo(db)
        _seed_mvp5_demo(db)
        _seed_mvp6_demo(db)
        _seed_mvp7_demo(db)
        _seed_mvp8_demo(db)
        _seed_mvp11_demo(db)
        _seed_mvp14_demo(db)
        _seed_mvp15_20_demo(db)
        _seed_production_phase1_demo(db)
        return

    entities = [
        LegalEntity(name="GlobalTech India", country_code="IN", functional_currency="INR", reporting_currency="USD", minimum_cash=Decimal("900000000")),
        LegalEntity(name="GlobalTech USA", country_code="US", functional_currency="USD", reporting_currency="USD", minimum_cash=Decimal("18000000"), is_treasury_centre=True),
        LegalEntity(name="GlobalTech Germany", country_code="DE", functional_currency="EUR", reporting_currency="USD", minimum_cash=Decimal("12000000")),
        LegalEntity(name="GlobalTech Singapore", country_code="SG", functional_currency="SGD", reporting_currency="USD", minimum_cash=Decimal("9000000"), is_treasury_centre=True),
        LegalEntity(name="GlobalTech UK", country_code="GB", functional_currency="GBP", reporting_currency="USD", minimum_cash=Decimal("8000000")),
        LegalEntity(name="GlobalTech Japan", country_code="JP", functional_currency="JPY", reporting_currency="USD", minimum_cash=Decimal("1200000000")),
    ]
    db.add_all(entities)
    db.flush()
    e = {x.country_code: x for x in entities}

    now = datetime.now(UTC).replace(tzinfo=None)
    db.add_all([
        BankAccount(entity_id=e["IN"].id, bank_name="HDFC Bank", country_code="IN", currency="INR", book_balance=Decimal("2100000000"), restricted_balance=Decimal("160000000"), committed_outflows=Decimal("250000000"), last_updated=now),
        BankAccount(entity_id=e["US"].id, bank_name="JPMorgan", country_code="US", currency="USD", book_balance=Decimal("42000000"), restricted_balance=Decimal("2000000"), committed_outflows=Decimal("6000000"), last_updated=now),
        BankAccount(entity_id=e["DE"].id, bank_name="Deutsche Bank", country_code="DE", currency="EUR", book_balance=Decimal("18500000"), restricted_balance=Decimal("1500000"), committed_outflows=Decimal("3000000"), last_updated=now),
        BankAccount(entity_id=e["SG"].id, bank_name="DBS", country_code="SG", currency="SGD", book_balance=Decimal("26000000"), restricted_balance=Decimal("1000000"), committed_outflows=Decimal("4000000"), last_updated=now),
        BankAccount(entity_id=e["GB"].id, bank_name="HSBC", country_code="GB", currency="GBP", book_balance=Decimal("10500000"), restricted_balance=Decimal("500000"), committed_outflows=Decimal("2500000"), last_updated=now),
        BankAccount(entity_id=e["JP"].id, bank_name="MUFG", country_code="JP", currency="JPY", book_balance=Decimal("2300000000"), restricted_balance=Decimal("200000000"), committed_outflows=Decimal("450000000"), last_updated=now - timedelta(hours=30)),
    ])

    db.add_all([
        CreditFacility(entity_id=e["IN"].id, lender="State Bank of India", currency="INR", limit_amount=Decimal("1500000000"), drawn_amount=Decimal("400000000"), maturity_date=date.today() + timedelta(days=420)),
        CreditFacility(entity_id=e["US"].id, lender="JPMorgan", currency="USD", limit_amount=Decimal("40000000"), drawn_amount=Decimal("10000000"), maturity_date=date.today() + timedelta(days=240)),
        CreditFacility(entity_id=e["DE"].id, lender="Deutsche Bank", currency="EUR", limit_amount=Decimal("20000000"), drawn_amount=Decimal("17000000"), maturity_date=date.today() + timedelta(days=75)),
        CreditFacility(entity_id=e["SG"].id, lender="DBS", currency="SGD", limit_amount=Decimal("15000000"), drawn_amount=Decimal("2000000"), maturity_date=date.today() + timedelta(days=500)),
    ])

    db.add_all([
        FXRate(base_currency="USD", quote_currency="INR", rate=Decimal("92.10"), as_of=now),
        FXRate(base_currency="EUR", quote_currency="USD", rate=Decimal("1.17"), as_of=now),
        FXRate(base_currency="GBP", quote_currency="USD", rate=Decimal("1.34"), as_of=now),
        FXRate(base_currency="USD", quote_currency="JPY", rate=Decimal("149.00"), as_of=now),
        FXRate(base_currency="USD", quote_currency="SGD", rate=Decimal("1.29"), as_of=now),
    ])

    db.add_all([
        CashFlow(entity_id=e["IN"].id, flow_type="RECEIVABLE", counterparty="US Distributor", currency="USD", amount=Decimal("18000000"), due_date=date.today()+timedelta(days=20), probability=Decimal("0.86")),
        CashFlow(entity_id=e["IN"].id, flow_type="PAYABLE", counterparty="US Vendor", currency="USD", amount=Decimal("9000000"), due_date=date.today()+timedelta(days=15), probability=Decimal("1.00")),
        CashFlow(entity_id=e["DE"].id, flow_type="RECEIVABLE", counterparty="EU Customer", currency="EUR", amount=Decimal("12000000"), due_date=date.today()+timedelta(days=25), probability=Decimal("0.95")),
        CashFlow(entity_id=e["GB"].id, flow_type="PAYABLE", counterparty="UK Supplier", currency="GBP", amount=Decimal("6000000"), due_date=date.today()+timedelta(days=10), probability=Decimal("1.00")),
    ])

    db.add_all([
        DerivativePosition(entity_id=e["IN"].id, instrument_type="FX_FORWARD", counterparty="HDFC Bank", exposure_currency="USD", notional=Decimal("6000000"), hedge_direction="SELL", maturity_date=date.today()+timedelta(days=30), market_value_reporting_ccy=Decimal("150000"), hedge_designation="USD_RECEIVABLE_HEDGE", underlying_reference="AR-USD-PORTFOLIO"),
        DerivativePosition(entity_id=e["DE"].id, instrument_type="FX_FORWARD", counterparty="Deutsche Bank", exposure_currency="EUR", notional=Decimal("5000000"), hedge_direction="SELL", maturity_date=date.today()+timedelta(days=45), market_value_reporting_ccy=Decimal("-80000"), hedge_designation="EUR_NET_EXPOSURE", underlying_reference="EU-AR-PORTFOLIO"),
    ])

    db.add_all([
        TreasuryPolicy(policy_code="MINIMUM_ENTITY_CASH", description="Each entity must remain above approved minimum cash", threshold_value=None),
        TreasuryPolicy(policy_code="NO_SPECULATIVE_DERIVATIVES", description="Derivatives must map to approved underlying exposures", threshold_value=None),
        TreasuryPolicy(policy_code="FACILITY_UTILIZATION_WARNING", description="Escalate committed facility utilization at or above 80%", threshold_value=Decimal("0.8")),
    ])
    db.commit()
    _seed_forecast_demo(db)
    _seed_market_risk_demo(db)
    _seed_mvp4_demo(db)
    _seed_mvp5_demo(db)
    _seed_mvp6_demo(db)
    _seed_mvp7_demo(db)
    _seed_mvp8_demo(db)
    _seed_mvp11_demo(db)
    _seed_mvp14_demo(db)
    _seed_mvp15_20_demo(db)
    _seed_production_phase1_demo(db)
