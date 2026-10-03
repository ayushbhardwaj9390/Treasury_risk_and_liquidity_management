from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class LegalEntity(Base):
    __tablename__ = "legal_entities"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    country_code: Mapped[str] = mapped_column(String(2), index=True)
    functional_currency: Mapped[str] = mapped_column(String(3))
    reporting_currency: Mapped[str] = mapped_column(String(3), default="USD")
    minimum_cash: Mapped[Decimal] = mapped_column(Numeric(20, 4), default=0)
    is_treasury_centre: Mapped[bool] = mapped_column(Boolean, default=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    bank_accounts: Mapped[list["BankAccount"]] = relationship(back_populates="entity")
    credit_facilities: Mapped[list["CreditFacility"]] = relationship(back_populates="entity")


class BankAccount(Base):
    __tablename__ = "bank_accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_id: Mapped[int] = mapped_column(ForeignKey("legal_entities.id"), index=True)
    bank_name: Mapped[str] = mapped_column(String(120))
    country_code: Mapped[str] = mapped_column(String(2))
    currency: Mapped[str] = mapped_column(String(3), index=True)
    account_type: Mapped[str] = mapped_column(String(40), default="OPERATING")
    book_balance: Mapped[Decimal] = mapped_column(Numeric(20, 4), default=0)
    restricted_balance: Mapped[Decimal] = mapped_column(Numeric(20, 4), default=0)
    committed_outflows: Mapped[Decimal] = mapped_column(Numeric(20, 4), default=0)
    last_updated: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None))

    entity: Mapped[LegalEntity] = relationship(back_populates="bank_accounts")


class CreditFacility(Base):
    __tablename__ = "credit_facilities"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_id: Mapped[int] = mapped_column(ForeignKey("legal_entities.id"), index=True)
    lender: Mapped[str] = mapped_column(String(120))
    currency: Mapped[str] = mapped_column(String(3))
    limit_amount: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    drawn_amount: Mapped[Decimal] = mapped_column(Numeric(20, 4), default=0)
    maturity_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    committed: Mapped[bool] = mapped_column(Boolean, default=True)

    entity: Mapped[LegalEntity] = relationship(back_populates="credit_facilities")


class FXRate(Base):
    __tablename__ = "fx_rates"

    id: Mapped[int] = mapped_column(primary_key=True)
    base_currency: Mapped[str] = mapped_column(String(3), index=True)
    quote_currency: Mapped[str] = mapped_column(String(3), index=True)
    rate: Mapped[Decimal] = mapped_column(Numeric(20, 8))
    as_of: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None), index=True)
    source: Mapped[str] = mapped_column(String(80), default="SYNTHETIC")


class CashFlow(Base):
    __tablename__ = "cash_flows"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_id: Mapped[int] = mapped_column(ForeignKey("legal_entities.id"), index=True)
    flow_type: Mapped[str] = mapped_column(String(20))  # RECEIVABLE / PAYABLE
    counterparty: Mapped[str] = mapped_column(String(160))
    currency: Mapped[str] = mapped_column(String(3), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    due_date: Mapped[date] = mapped_column(Date, index=True)
    probability: Mapped[Decimal] = mapped_column(Numeric(8, 6), default=1)
    status: Mapped[str] = mapped_column(String(30), default="OPEN")
    source_reference: Mapped[str | None] = mapped_column(String(180), nullable=True, index=True)


class DerivativePosition(Base):
    __tablename__ = "derivative_positions"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_id: Mapped[int] = mapped_column(ForeignKey("legal_entities.id"), index=True)
    instrument_type: Mapped[str] = mapped_column(String(40), index=True)
    counterparty: Mapped[str] = mapped_column(String(120), index=True)
    exposure_currency: Mapped[str] = mapped_column(String(3), index=True)
    notional: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    hedge_direction: Mapped[str] = mapped_column(String(16))  # BUY/SELL/PAY_FIXED/RECEIVE_FIXED
    maturity_date: Mapped[date] = mapped_column(Date, index=True)
    market_value_reporting_ccy: Mapped[Decimal] = mapped_column(Numeric(20, 4), default=0)
    hedge_designation: Mapped[str | None] = mapped_column(String(80), nullable=True)
    underlying_reference: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="OPEN", index=True)


class DebtPosition(Base):
    __tablename__ = "debt_positions"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_id: Mapped[int] = mapped_column(ForeignKey("legal_entities.id"), index=True)
    lender: Mapped[str] = mapped_column(String(120), index=True)
    currency: Mapped[str] = mapped_column(String(3), index=True)
    principal: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    rate_type: Mapped[str] = mapped_column(String(16), index=True)  # FIXED / FLOATING
    coupon_rate: Mapped[Decimal] = mapped_column(Numeric(12, 8), default=0)
    benchmark: Mapped[str | None] = mapped_column(String(40), nullable=True)
    spread_bps: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=0)
    maturity_date: Mapped[date] = mapped_column(Date, index=True)
    status: Mapped[str] = mapped_column(String(20), default="OPEN", index=True)


class CounterpartyLimit(Base):
    __tablename__ = "counterparty_limits"

    id: Mapped[int] = mapped_column(primary_key=True)
    counterparty: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    exposure_limit_reporting_ccy: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    warning_utilization: Mapped[Decimal] = mapped_column(Numeric(8, 6), default=Decimal("0.8"))
    credit_rating: Mapped[str | None] = mapped_column(String(20), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class TreasuryPolicy(Base):
    __tablename__ = "treasury_policies"

    id: Mapped[int] = mapped_column(primary_key=True)
    policy_code: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    description: Mapped[str] = mapped_column(String(300))
    threshold_value: Mapped[Decimal | None] = mapped_column(Numeric(20, 6), nullable=True)
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_type: Mapped[str] = mapped_column(String(80), index=True)
    actor: Mapped[str] = mapped_column(String(120), default="SYSTEM")
    details: Mapped[str] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None), index=True)


class CashRestriction(Base):
    __tablename__ = "cash_restrictions"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_id: Mapped[int] = mapped_column(ForeignKey("legal_entities.id"), index=True)
    restriction_type: Mapped[str] = mapped_column(String(40), index=True)  # REGULATORY / TAX / OPERATIONAL / LEGAL
    currency: Mapped[str] = mapped_column(String(3), index=True)
    restricted_amount: Mapped[Decimal] = mapped_column(Numeric(20, 4), default=0)
    description: Mapped[str] = mapped_column(String(300))
    effective_from: Mapped[date] = mapped_column(Date, default=date.today)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=True)
    source_reference: Mapped[str] = mapped_column(String(160), default="SYNTHETIC_POLICY")
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)


class CashPool(Base):
    __tablename__ = "cash_pools"

    id: Mapped[int] = mapped_column(primary_key=True)
    pool_name: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    header_entity_id: Mapped[int] = mapped_column(ForeignKey("legal_entities.id"), index=True)
    pool_type: Mapped[str] = mapped_column(String(30), default="PHYSICAL")  # PHYSICAL / NOTIONAL
    currency: Mapped[str] = mapped_column(String(3), index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class CashPoolMember(Base):
    __tablename__ = "cash_pool_members"

    id: Mapped[int] = mapped_column(primary_key=True)
    cash_pool_id: Mapped[int] = mapped_column(ForeignKey("cash_pools.id"), index=True)
    entity_id: Mapped[int] = mapped_column(ForeignKey("legal_entities.id"), index=True)
    sweep_target_local: Mapped[Decimal] = mapped_column(Numeric(20, 4), default=0)
    can_contribute: Mapped[bool] = mapped_column(Boolean, default=True)
    can_receive: Mapped[bool] = mapped_column(Boolean, default=True)


class IntercompanyFacility(Base):
    __tablename__ = "intercompany_facilities"

    id: Mapped[int] = mapped_column(primary_key=True)
    lender_entity_id: Mapped[int] = mapped_column(ForeignKey("legal_entities.id"), index=True)
    borrower_entity_id: Mapped[int] = mapped_column(ForeignKey("legal_entities.id"), index=True)
    currency: Mapped[str] = mapped_column(String(3), index=True)
    limit_amount: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    drawn_amount: Mapped[Decimal] = mapped_column(Numeric(20, 4), default=0)
    interest_rate: Mapped[Decimal] = mapped_column(Numeric(12, 8), default=0)
    maturity_date: Mapped[date] = mapped_column(Date, index=True)
    transfer_pricing_min_rate: Mapped[Decimal | None] = mapped_column(Numeric(12, 8), nullable=True)
    transfer_pricing_max_rate: Mapped[Decimal | None] = mapped_column(Numeric(12, 8), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="AVAILABLE", index=True)


class TaxRule(Base):
    __tablename__ = "tax_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    from_country_code: Mapped[str] = mapped_column(String(2), index=True)
    to_country_code: Mapped[str] = mapped_column(String(2), index=True)
    cash_flow_type: Mapped[str] = mapped_column(String(30), index=True)  # INTEREST / DIVIDEND / FEE
    rule_type: Mapped[str] = mapped_column(String(30), default="WITHHOLDING_TAX")
    rate: Mapped[Decimal] = mapped_column(Numeric(12, 8), default=0)
    effective_from: Mapped[date] = mapped_column(Date, default=date.today)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    source_reference: Mapped[str] = mapped_column(String(180), default="SYNTHETIC_DEMO")
    version: Mapped[str] = mapped_column(String(40), default="1.0")
    review_status: Mapped[str] = mapped_column(String(30), default="REVIEW_REQUIRED")
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)


class CollateralAgreement(Base):
    __tablename__ = "collateral_agreements"

    id: Mapped[int] = mapped_column(primary_key=True)
    counterparty: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    agreement_type: Mapped[str] = mapped_column(String(30), default="CSA")
    threshold_reporting_ccy: Mapped[Decimal] = mapped_column(Numeric(20, 4), default=0)
    minimum_transfer_amount_reporting_ccy: Mapped[Decimal] = mapped_column(Numeric(20, 4), default=0)
    independent_amount_reporting_ccy: Mapped[Decimal] = mapped_column(Numeric(20, 4), default=0)
    collateral_posted_reporting_ccy: Mapped[Decimal] = mapped_column(Numeric(20, 4), default=0)
    collateral_received_reporting_ccy: Mapped[Decimal] = mapped_column(Numeric(20, 4), default=0)
    eligible_collateral_currency: Mapped[str] = mapped_column(String(3), default="USD")
    haircut: Mapped[Decimal] = mapped_column(Numeric(8, 6), default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class CovenantTest(Base):
    __tablename__ = "covenant_tests"

    id: Mapped[int] = mapped_column(primary_key=True)
    debt_position_id: Mapped[int] = mapped_column(ForeignKey("debt_positions.id"), index=True)
    covenant_code: Mapped[str] = mapped_column(String(80), index=True)
    metric_name: Mapped[str] = mapped_column(String(120))
    threshold_value: Mapped[Decimal] = mapped_column(Numeric(20, 8))
    current_value: Mapped[Decimal] = mapped_column(Numeric(20, 8))
    direction: Mapped[str] = mapped_column(String(10))  # MIN / MAX
    warning_buffer_pct: Mapped[Decimal] = mapped_column(Numeric(8, 6), default=Decimal("0.10"))
    testing_date: Mapped[date] = mapped_column(Date, index=True)
    source_reference: Mapped[str] = mapped_column(String(160), default="SYNTHETIC_FACILITY_AGREEMENT")
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)


class UserAccount(Base):
    __tablename__ = "user_accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(40), index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class MarketDataFeed(Base):
    __tablename__ = "market_data_feeds"

    id: Mapped[int] = mapped_column(primary_key=True)
    feed_name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    asset_class: Mapped[str] = mapped_column(String(40), index=True)
    source_type: Mapped[str] = mapped_column(String(30), default="PRIMARY")
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE", index=True)
    last_received_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None))
    stale_after_minutes: Mapped[int] = mapped_column(default=15)
    required_for_execution: Mapped[bool] = mapped_column(Boolean, default=True)


class SourceConnector(Base):
    __tablename__ = "source_connectors"

    id: Mapped[int] = mapped_column(primary_key=True)
    connector_name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    connector_type: Mapped[str] = mapped_column(String(30), index=True)  # BANK / ERP / MARKET / TAX
    system_name: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE", index=True)
    last_success_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None))
    stale_after_minutes: Mapped[int] = mapped_column(default=60)
    required_for_execution: Mapped[bool] = mapped_column(Boolean, default=True)
    owner: Mapped[str] = mapped_column(String(120), default="TREASURY_TECH")


class ReconciliationRun(Base):
    __tablename__ = "reconciliation_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    connector_id: Mapped[int] = mapped_column(ForeignKey("source_connectors.id"), index=True)
    run_type: Mapped[str] = mapped_column(String(40), index=True)
    source_total: Mapped[Decimal] = mapped_column(Numeric(20, 4), default=0)
    target_total: Mapped[Decimal] = mapped_column(Numeric(20, 4), default=0)
    difference: Mapped[Decimal] = mapped_column(Numeric(20, 4), default=0)
    unmatched_count: Mapped[int] = mapped_column(default=0)
    status: Mapped[str] = mapped_column(String(20), default="PASS", index=True)
    run_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None), index=True)


class HedgeAccountingDesignation(Base):
    __tablename__ = "hedge_accounting_designations"

    id: Mapped[int] = mapped_column(primary_key=True)
    derivative_position_id: Mapped[int] = mapped_column(ForeignKey("derivative_positions.id"), unique=True, index=True)
    designation_type: Mapped[str] = mapped_column(String(40), index=True)
    hedged_item_reference: Mapped[str] = mapped_column(String(160))
    risk_component: Mapped[str] = mapped_column(String(80))
    hedge_ratio: Mapped[Decimal] = mapped_column(Numeric(12, 8), default=1)
    documentation_status: Mapped[str] = mapped_column(String(30), default="DRAFT", index=True)
    effectiveness_status: Mapped[str] = mapped_column(String(30), default="NOT_TESTED", index=True)
    designation_date: Mapped[date] = mapped_column(Date, default=date.today)
    last_tested_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    accounting_standard: Mapped[str] = mapped_column(String(40), default="IFRS_9")


class TransactionProposal(Base):
    __tablename__ = "transaction_proposals"

    id: Mapped[int] = mapped_column(primary_key=True)
    proposal_type: Mapped[str] = mapped_column(String(40), index=True)
    source_entity_id: Mapped[int | None] = mapped_column(ForeignKey("legal_entities.id"), nullable=True, index=True)
    target_entity_id: Mapped[int | None] = mapped_column(ForeignKey("legal_entities.id"), nullable=True, index=True)
    counterparty: Mapped[str | None] = mapped_column(String(120), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    purpose: Mapped[str] = mapped_column(String(300))
    underlying_reference: Mapped[str | None] = mapped_column(String(160), nullable=True)
    created_by: Mapped[str] = mapped_column(String(80), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None), index=True)
    status: Mapped[str] = mapped_column(String(30), default="DRAFT", index=True)
    control_status: Mapped[str] = mapped_column(String(30), default="PENDING", index=True)
    control_summary: Mapped[str] = mapped_column(Text, default="")
    required_approvals: Mapped[int] = mapped_column(default=1)
    executed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class ApprovalDecision(Base):
    __tablename__ = "approval_decisions"

    id: Mapped[int] = mapped_column(primary_key=True)
    proposal_id: Mapped[int] = mapped_column(ForeignKey("transaction_proposals.id"), index=True)
    actor: Mapped[str] = mapped_column(String(80), index=True)
    actor_role: Mapped[str] = mapped_column(String(40))
    decision: Mapped[str] = mapped_column(String(20), index=True)  # APPROVE / REJECT
    comment: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None), index=True)


class ScenarioTemplate(Base):
    __tablename__ = "scenario_templates"

    id: Mapped[int] = mapped_column(primary_key=True)
    scenario_code: Mapped[str] = mapped_column(String(60), unique=True, index=True)
    label: Mapped[str] = mapped_column(String(120))
    receivable_multiplier: Mapped[Decimal] = mapped_column(Numeric(12, 8), default=1)
    payable_multiplier: Mapped[Decimal] = mapped_column(Numeric(12, 8), default=1)
    facility_availability: Mapped[Decimal] = mapped_column(Numeric(12, 8), default=1)
    fx_shock_pct: Mapped[Decimal] = mapped_column(Numeric(12, 8), default=0)
    rate_shock_bps: Mapped[int] = mapped_column(default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)


class PaymentHistory(Base):
    __tablename__ = "payment_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_id: Mapped[int] = mapped_column(ForeignKey("legal_entities.id"), index=True)
    counterparty: Mapped[str] = mapped_column(String(160), index=True)
    country_code: Mapped[str] = mapped_column(String(2), index=True)
    currency: Mapped[str] = mapped_column(String(3), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    invoice_date: Mapped[date] = mapped_column(Date, index=True)
    due_date: Mapped[date] = mapped_column(Date, index=True)
    paid_date: Mapped[date] = mapped_column(Date, index=True)
    terms_days: Mapped[int] = mapped_column(default=30)
    source_reference: Mapped[str] = mapped_column(String(160), default="SYNTHETIC_ERP_HISTORY")


class IntradayPayment(Base):
    __tablename__ = "intraday_payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_id: Mapped[int] = mapped_column(ForeignKey("legal_entities.id"), index=True)
    payment_reference: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    direction: Mapped[str] = mapped_column(String(12), index=True)  # INFLOW / OUTFLOW
    payment_type: Mapped[str] = mapped_column(String(40), index=True)
    counterparty: Mapped[str] = mapped_column(String(160), index=True)
    currency: Mapped[str] = mapped_column(String(3), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    scheduled_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    status: Mapped[str] = mapped_column(String(24), default="SCHEDULED", index=True)
    source_reference: Mapped[str] = mapped_column(String(160), default="SYNTHETIC_PAYMENT_HUB")


class ModelRegistryEntry(Base):
    __tablename__ = "model_registry"

    id: Mapped[int] = mapped_column(primary_key=True)
    model_code: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    version: Mapped[str] = mapped_column(String(40), default="1.0.0")
    model_type: Mapped[str] = mapped_column(String(80))
    trained_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None), index=True)
    training_rows: Mapped[int] = mapped_column(default=0)
    validation_status: Mapped[str] = mapped_column(String(20), default="UNVALIDATED", index=True)
    metrics_json: Mapped[str] = mapped_column(Text, default="{}")
    feature_schema: Mapped[str] = mapped_column(Text, default="[]")
    data_fingerprint: Mapped[str] = mapped_column(String(128), default="")
    owner: Mapped[str] = mapped_column(String(120), default="TREASURY_MODEL_RISK")


class IndependentValuation(Base):
    __tablename__ = "independent_valuations"

    id: Mapped[int] = mapped_column(primary_key=True)
    derivative_position_id: Mapped[int] = mapped_column(ForeignKey("derivative_positions.id"), index=True)
    source_name: Mapped[str] = mapped_column(String(120), index=True)
    source_type: Mapped[str] = mapped_column(String(30), default="INDEPENDENT")
    independent_value_reporting_ccy: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    observed_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None), index=True)
    valuation_method: Mapped[str] = mapped_column(String(80), default="EXTERNAL_PRICER")


class PaymentScreeningCase(Base):
    __tablename__ = "payment_screening_cases"

    id: Mapped[int] = mapped_column(primary_key=True)
    payment_reference: Mapped[str] = mapped_column(String(100), index=True)
    counterparty: Mapped[str] = mapped_column(String(160), index=True)
    provider: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(24), index=True)  # CLEAR / POTENTIAL_MATCH / BLOCKED / PENDING
    screened_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None), index=True)
    list_version: Mapped[str] = mapped_column(String(80), default="SYNTHETIC_DEMO")
    reason: Mapped[str] = mapped_column(String(300), default="")


class DerivativeValuationTerms(Base):
    __tablename__ = "derivative_valuation_terms"

    id: Mapped[int] = mapped_column(primary_key=True)
    derivative_position_id: Mapped[int] = mapped_column(ForeignKey("derivative_positions.id"), unique=True, index=True)
    model_type: Mapped[str] = mapped_column(String(50), index=True)  # FX_FORWARD / GARMAN_KOHLHAGEN / IRS_PAR_RATE
    currency_pair: Mapped[str | None] = mapped_column(String(7), nullable=True)
    contracted_rate: Mapped[Decimal | None] = mapped_column(Numeric(20, 10), nullable=True)
    strike: Mapped[Decimal | None] = mapped_column(Numeric(20, 10), nullable=True)
    option_type: Mapped[str | None] = mapped_column(String(8), nullable=True)  # CALL / PUT
    fixed_rate: Mapped[Decimal | None] = mapped_column(Numeric(12, 8), nullable=True)
    floating_spread_bps: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=0)
    payment_frequency_per_year: Mapped[int] = mapped_column(default=4)
    notional_currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    source_reference: Mapped[str] = mapped_column(String(160), default="SYNTHETIC_MVP7_TERMS")


class MarketCurvePoint(Base):
    __tablename__ = "market_curve_points"

    id: Mapped[int] = mapped_column(primary_key=True)
    curve_name: Mapped[str] = mapped_column(String(100), index=True)
    currency: Mapped[str] = mapped_column(String(3), index=True)
    curve_type: Mapped[str] = mapped_column(String(30), default="DISCOUNT", index=True)
    tenor_days: Mapped[int] = mapped_column(index=True)
    zero_rate: Mapped[Decimal] = mapped_column(Numeric(12, 8))
    as_of: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None), index=True)
    source: Mapped[str] = mapped_column(String(120), default="SYNTHETIC_PRIMARY_CURVE")


class VolatilityQuote(Base):
    __tablename__ = "volatility_quotes"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_class: Mapped[str] = mapped_column(String(30), default="FX", index=True)
    underlying: Mapped[str] = mapped_column(String(20), index=True)
    tenor_days: Mapped[int] = mapped_column(index=True)
    quote_type: Mapped[str] = mapped_column(String(30), default="ATM")
    volatility: Mapped[Decimal] = mapped_column(Numeric(12, 8))
    as_of: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None), index=True)
    source: Mapped[str] = mapped_column(String(120), default="SYNTHETIC_PRIMARY_VOL")


class LegalNettingSet(Base):
    __tablename__ = "legal_netting_sets"

    id: Mapped[int] = mapped_column(primary_key=True)
    netting_set_code: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    counterparty: Mapped[str] = mapped_column(String(120), index=True)
    agreement_type: Mapped[str] = mapped_column(String(40), default="ISDA_MASTER")
    governing_law: Mapped[str] = mapped_column(String(80), default="ENGLISH_LAW")
    close_out_netting_enforceable: Mapped[bool] = mapped_column(Boolean, default=False)
    legal_opinion_status: Mapped[str] = mapped_column(String(30), default="REVIEW_REQUIRED", index=True)
    collateral_agreement_id: Mapped[int | None] = mapped_column(ForeignKey("collateral_agreements.id"), nullable=True)
    last_legal_review_date: Mapped[date | None] = mapped_column(Date, nullable=True)


class NettingSetTrade(Base):
    __tablename__ = "netting_set_trades"

    id: Mapped[int] = mapped_column(primary_key=True)
    netting_set_id: Mapped[int] = mapped_column(ForeignKey("legal_netting_sets.id"), index=True)
    derivative_position_id: Mapped[int] = mapped_column(ForeignKey("derivative_positions.id"), unique=True, index=True)


class ModelDeployment(Base):
    __tablename__ = "model_deployments"

    id: Mapped[int] = mapped_column(primary_key=True)
    model_code: Mapped[str] = mapped_column(String(100), index=True)
    version: Mapped[str] = mapped_column(String(40))
    deployment_role: Mapped[str] = mapped_column(String(20), index=True)  # CHAMPION / CHALLENGER
    approval_status: Mapped[str] = mapped_column(String(24), default="PENDING", index=True)
    effective_from: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None))
    approved_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    promotion_threshold_pct: Mapped[Decimal] = mapped_column(Numeric(12, 6), default=Decimal("0.05"))
    notes: Mapped[str] = mapped_column(String(500), default="")


class ResilienceControl(Base):
    __tablename__ = "resilience_controls"

    id: Mapped[int] = mapped_column(primary_key=True)
    component_name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    criticality_tier: Mapped[str] = mapped_column(String(20), default="TIER_1", index=True)
    rto_minutes: Mapped[int] = mapped_column(default=60)
    rpo_minutes: Mapped[int] = mapped_column(default=15)
    multi_region: Mapped[bool] = mapped_column(Boolean, default=False)
    last_dr_test_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_dr_test_result: Mapped[str] = mapped_column(String(20), default="NOT_TESTED", index=True)
    owner: Mapped[str] = mapped_column(String(120), default="TREASURY_TECH")


class TreasuryEvent(Base):
    __tablename__ = "treasury_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    idempotency_key: Mapped[str] = mapped_column(String(180), unique=True, index=True)
    event_type: Mapped[str] = mapped_column(String(60), index=True)
    source_system: Mapped[str] = mapped_column(String(120), index=True)
    connector_name: Mapped[str] = mapped_column(String(120), index=True)
    entity_id: Mapped[int | None] = mapped_column(ForeignKey("legal_entities.id"), nullable=True, index=True)
    external_reference: Mapped[str | None] = mapped_column(String(180), nullable=True, index=True)
    sequence_no: Mapped[int | None] = mapped_column(nullable=True)
    schema_version: Mapped[str] = mapped_column(String(20), default="1.0")
    event_time: Mapped[datetime] = mapped_column(DateTime, index=True)
    received_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None), index=True)
    payload_hash: Mapped[str] = mapped_column(String(64), index=True)
    payload_json: Mapped[str] = mapped_column(Text)
    processing_status: Mapped[str] = mapped_column(String(40), default="RECEIVED", index=True)
    processing_error: Mapped[str] = mapped_column(String(500), default="")
    replay_count: Mapped[int] = mapped_column(default=0)


class ConnectorCheckpoint(Base):
    __tablename__ = "connector_checkpoints"

    id: Mapped[int] = mapped_column(primary_key=True)
    connector_name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    source_system: Mapped[str] = mapped_column(String(120), index=True)
    last_sequence_no: Mapped[int | None] = mapped_column(nullable=True)
    last_event_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    last_received_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    accepted_count: Mapped[int] = mapped_column(default=0)
    duplicate_count: Mapped[int] = mapped_column(default=0)
    quarantined_count: Mapped[int] = mapped_column(default=0)
    failed_count: Mapped[int] = mapped_column(default=0)
    status: Mapped[str] = mapped_column(String(24), default="ACTIVE", index=True)


class ExecutionMessage(Base):
    __tablename__ = "execution_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    message_id: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    proposal_id: Mapped[int] = mapped_column(ForeignKey("transaction_proposals.id"), index=True)
    connector_name: Mapped[str] = mapped_column(String(120), index=True)
    idempotency_key: Mapped[str] = mapped_column(String(180), unique=True, index=True)
    payload_hash: Mapped[str] = mapped_column(String(64))
    payload_json: Mapped[str] = mapped_column(Text)
    signature: Mapped[str] = mapped_column(String(128), default="DEMO_UNVERIFIED")
    status: Mapped[str] = mapped_column(String(32), default="QUEUED", index=True)
    created_by: Mapped[str] = mapped_column(String(80), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None), index=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    external_reference: Mapped[str | None] = mapped_column(String(180), nullable=True, index=True)
    acknowledgement_detail: Mapped[str] = mapped_column(String(500), default="")


class LiveTreasuryAlert(Base):
    __tablename__ = "live_treasury_alerts"

    id: Mapped[int] = mapped_column(primary_key=True)
    alert_key: Mapped[str] = mapped_column(String(180), unique=True, index=True)
    category: Mapped[str] = mapped_column(String(60), index=True)
    severity: Mapped[str] = mapped_column(String(20), index=True)
    title: Mapped[str] = mapped_column(String(180))
    message: Mapped[str] = mapped_column(String(800))
    source_event_id: Mapped[int | None] = mapped_column(ForeignKey("treasury_events.id"), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(24), default="OPEN", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None), index=True)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None), index=True)
    acknowledged_by: Mapped[str | None] = mapped_column(String(80), nullable=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class MarketReturnObservation(Base):
    __tablename__ = "market_return_observations"

    id: Mapped[int] = mapped_column(primary_key=True)
    observation_date: Mapped[date] = mapped_column(Date, index=True)
    factor_type: Mapped[str] = mapped_column(String(30), default="FX", index=True)
    factor_key: Mapped[str] = mapped_column(String(40), index=True)
    return_value: Mapped[Decimal] = mapped_column(Numeric(16, 10))
    source: Mapped[str] = mapped_column(String(120), default="SYNTHETIC_HISTORICAL_MARKET")
    approved: Mapped[bool] = mapped_column(Boolean, default=True, index=True)


class CounterpartyCreditMetric(Base):
    __tablename__ = "counterparty_credit_metrics"

    id: Mapped[int] = mapped_column(primary_key=True)
    counterparty: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    one_year_pd: Mapped[Decimal] = mapped_column(Numeric(12, 8), default=Decimal("0.01"))
    lgd: Mapped[Decimal] = mapped_column(Numeric(12, 8), default=Decimal("0.60"))
    funding_spread_bps: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=Decimal("100"))
    as_of: Mapped[date] = mapped_column(Date, default=date.today, index=True)
    source: Mapped[str] = mapped_column(String(160), default="SYNTHETIC_CREDIT_RISK")
    approved: Mapped[bool] = mapped_column(Boolean, default=False, index=True)


class TreasuryRiskLimit(Base):
    __tablename__ = "treasury_risk_limits"

    id: Mapped[int] = mapped_column(primary_key=True)
    limit_code: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    category: Mapped[str] = mapped_column(String(60), index=True)
    metric_name: Mapped[str] = mapped_column(String(120), index=True)
    comparator: Mapped[str] = mapped_column(String(8), default="MAX")  # MAX / MIN
    threshold_value: Mapped[Decimal] = mapped_column(Numeric(24, 8))
    warning_utilization: Mapped[Decimal] = mapped_column(Numeric(12, 8), default=Decimal("0.80"))
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    effective_from: Mapped[date] = mapped_column(Date, default=date.today)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    owner: Mapped[str] = mapped_column(String(120), default="GROUP_TREASURY_RISK")
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)


class ForecastPerformanceRecord(Base):
    __tablename__ = "forecast_performance_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_id: Mapped[int] = mapped_column(ForeignKey("legal_entities.id"), index=True)
    forecast_date: Mapped[date] = mapped_column(Date, index=True)
    target_date: Mapped[date] = mapped_column(Date, index=True)
    flow_type: Mapped[str] = mapped_column(String(20), index=True)  # RECEIVABLE / PAYABLE
    counterparty: Mapped[str] = mapped_column(String(160), index=True)
    currency: Mapped[str] = mapped_column(String(3), index=True)
    forecast_amount: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    actual_amount: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    model_code: Mapped[str] = mapped_column(String(100), default="TREASURY_CASH_FORECAST", index=True)
    horizon_days: Mapped[int] = mapped_column(default=7, index=True)
    source_reference: Mapped[str] = mapped_column(String(160), default="SYNTHETIC_FORECAST_HISTORY")


class WorkingCapitalObservation(Base):
    __tablename__ = "working_capital_observations"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_id: Mapped[int] = mapped_column(ForeignKey("legal_entities.id"), index=True)
    period_end: Mapped[date] = mapped_column(Date, index=True)
    currency: Mapped[str] = mapped_column(String(3), index=True)
    revenue: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    cogs: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    receivables_balance: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    payables_balance: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    inventory_balance: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    source_reference: Mapped[str] = mapped_column(String(160), default="SYNTHETIC_WORKING_CAPITAL")


class CrossBorderConstraint(Base):
    __tablename__ = "cross_border_constraints"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_country: Mapped[str] = mapped_column(String(2), index=True)
    target_country: Mapped[str] = mapped_column(String(2), index=True)
    transfer_type: Mapped[str] = mapped_column(String(40), index=True)  # SWEEP / IC_LOAN / DIVIDEND
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    max_amount_reporting: Mapped[Decimal | None] = mapped_column(Numeric(20, 4), nullable=True)
    withholding_tax_rate: Mapped[Decimal] = mapped_column(Numeric(12, 8), default=0)
    regulatory_status: Mapped[str] = mapped_column(String(30), default="REVIEW_REQUIRED", index=True)
    legal_status: Mapped[str] = mapped_column(String(30), default="REVIEW_REQUIRED", index=True)
    requires_tax_review: Mapped[bool] = mapped_column(Boolean, default=True)
    requires_legal_review: Mapped[bool] = mapped_column(Boolean, default=True)
    effective_from: Mapped[date] = mapped_column(Date, default=date.today)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    source_reference: Mapped[str] = mapped_column(String(160), default="SYNTHETIC_MVP15")


class EnterpriseConnectorProfile(Base):
    __tablename__ = "enterprise_connector_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    connector_code: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    connector_type: Mapped[str] = mapped_column(String(30), index=True)  # BANK / ERP / MARKET / TMS / TAX
    system_name: Mapped[str] = mapped_column(String(120))
    protocol: Mapped[str] = mapped_column(String(40), default="API")
    auth_mode: Mapped[str] = mapped_column(String(40), default="WORKLOAD_IDENTITY")
    environment: Mapped[str] = mapped_column(String(20), default="UAT", index=True)
    status: Mapped[str] = mapped_column(String(20), default="CONFIGURED", index=True)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    latency_ms: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    error_rate: Mapped[Decimal] = mapped_column(Numeric(12, 8), default=0)
    supports_idempotency: Mapped[bool] = mapped_column(Boolean, default=True)
    supports_reconciliation: Mapped[bool] = mapped_column(Boolean, default=True)
    data_contract_version: Mapped[str] = mapped_column(String(30), default="1.0")


class SecurityControlRecord(Base):
    __tablename__ = "security_control_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    control_code: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    domain: Mapped[str] = mapped_column(String(50), index=True)
    required: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(20), default="NOT_TESTED", index=True)
    evidence: Mapped[str] = mapped_column(Text, default="")
    owner: Mapped[str] = mapped_column(String(100), default="SECURITY")
    last_tested_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class ModelValidationRecord(Base):
    __tablename__ = "model_validation_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    model_code: Mapped[str] = mapped_column(String(100), index=True)
    validation_type: Mapped[str] = mapped_column(String(50), index=True)  # BACKTEST / BENCHMARK / STABILITY
    metric_name: Mapped[str] = mapped_column(String(80))
    metric_value: Mapped[Decimal] = mapped_column(Numeric(20, 8))
    threshold_value: Mapped[Decimal] = mapped_column(Numeric(20, 8))
    comparison: Mapped[str] = mapped_column(String(4), default="LE")
    status: Mapped[str] = mapped_column(String(20), index=True)
    window_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    window_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    validated_by: Mapped[str] = mapped_column(String(100), default="INDEPENDENT_MODEL_RISK")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None), index=True)
    notes: Mapped[str] = mapped_column(Text, default="")


class InvestigationCase(Base):
    __tablename__ = "investigation_cases"

    id: Mapped[int] = mapped_column(primary_key=True)
    case_type: Mapped[str] = mapped_column(String(50), index=True)
    severity: Mapped[str] = mapped_column(String(20), index=True)
    status: Mapped[str] = mapped_column(String(24), default="OPEN", index=True)
    owner_role: Mapped[str] = mapped_column(String(50), index=True)
    entity_id: Mapped[int | None] = mapped_column(ForeignKey("legal_entities.id"), nullable=True, index=True)
    reference: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(200))
    details: Mapped[str] = mapped_column(Text, default="")
    opened_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None), index=True)


class DeploymentReadinessControl(Base):
    __tablename__ = "deployment_readiness_controls"

    id: Mapped[int] = mapped_column(primary_key=True)
    control_code: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    category: Mapped[str] = mapped_column(String(50), index=True)
    environment: Mapped[str] = mapped_column(String(20), default="PRODUCTION", index=True)
    required: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(20), default="NOT_READY", index=True)
    evidence: Mapped[str] = mapped_column(Text, default="")
    owner: Mapped[str] = mapped_column(String(100), default="PLATFORM")
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


# Production Phase 1: real data integration and lineage
class ExternalReferenceMap(Base):
    __tablename__ = "external_reference_maps"
    __table_args__ = (UniqueConstraint("connector_code", "object_type", "external_id", name="uq_external_reference_map"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    connector_code: Mapped[str] = mapped_column(String(80), index=True)
    object_type: Mapped[str] = mapped_column(String(40), index=True)  # BANK_ACCOUNT / LEGAL_ENTITY / INSTRUMENT
    external_id: Mapped[str] = mapped_column(String(180), index=True)
    internal_id: Mapped[int | None] = mapped_column(nullable=True, index=True)
    internal_code: Mapped[str | None] = mapped_column(String(180), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    source_reference: Mapped[str] = mapped_column(String(180), default="PHASE1_MAPPING")


class IntegrationRun(Base):
    __tablename__ = "integration_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    connector_code: Mapped[str] = mapped_column(String(80), index=True)
    run_type: Mapped[str] = mapped_column(String(50), index=True)
    status: Mapped[str] = mapped_column(String(30), default="STARTED", index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None), index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    records_received: Mapped[int] = mapped_column(default=0)
    records_applied: Mapped[int] = mapped_column(default=0)
    records_quarantined: Mapped[int] = mapped_column(default=0)
    source_total: Mapped[Decimal] = mapped_column(Numeric(24, 6), default=0)
    target_total: Mapped[Decimal] = mapped_column(Numeric(24, 6), default=0)
    difference: Mapped[Decimal] = mapped_column(Numeric(24, 6), default=0)
    watermark: Mapped[str | None] = mapped_column(String(180), nullable=True)
    payload_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    error_detail: Mapped[str] = mapped_column(Text, default="")


class DataLineageRecord(Base):
    __tablename__ = "data_lineage_records"
    __table_args__ = (UniqueConstraint("connector_code", "source_object_type", "source_record_id", "payload_hash", name="uq_data_lineage_source_hash"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    connector_code: Mapped[str] = mapped_column(String(80), index=True)
    source_system: Mapped[str] = mapped_column(String(120), index=True)
    source_object_type: Mapped[str] = mapped_column(String(60), index=True)
    source_record_id: Mapped[str] = mapped_column(String(180), index=True)
    target_table: Mapped[str] = mapped_column(String(80), index=True)
    target_record_id: Mapped[int | None] = mapped_column(nullable=True, index=True)
    source_timestamp: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    ingested_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None), index=True)
    payload_hash: Mapped[str] = mapped_column(String(64), index=True)
    schema_version: Mapped[str] = mapped_column(String(30), default="1.0")
    reconciliation_status: Mapped[str] = mapped_column(String(30), default="PENDING", index=True)


class IntegrationQuarantine(Base):
    __tablename__ = "integration_quarantine"

    id: Mapped[int] = mapped_column(primary_key=True)
    connector_code: Mapped[str] = mapped_column(String(80), index=True)
    record_type: Mapped[str] = mapped_column(String(60), index=True)
    source_reference: Mapped[str] = mapped_column(String(180), index=True)
    reason_code: Mapped[str] = mapped_column(String(80), index=True)
    reason_detail: Mapped[str] = mapped_column(Text, default="")
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    quarantined_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None), index=True)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    resolution: Mapped[str] = mapped_column(Text, default="")
    resolved_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class IntegrationCertificationControl(Base):
    __tablename__ = "integration_certification_controls"
    __table_args__ = (UniqueConstraint("connector_code", "control_code", name="uq_integration_cert_control"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    connector_code: Mapped[str] = mapped_column(String(80), index=True)
    control_code: Mapped[str] = mapped_column(String(100), index=True)
    required: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(24), default="NOT_TESTED", index=True)
    evidence: Mapped[str] = mapped_column(Text, default="")
    owner: Mapped[str] = mapped_column(String(100), default="TREASURY_TECH")
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class BankTransactionRecord(Base):
    __tablename__ = "bank_transaction_records"
    __table_args__ = (UniqueConstraint("connector_code", "source_record_id", name="uq_bank_transaction_source"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    connector_code: Mapped[str] = mapped_column(String(80), index=True)
    bank_account_id: Mapped[int | None] = mapped_column(ForeignKey("bank_accounts.id"), nullable=True, index=True)
    external_account_id: Mapped[str] = mapped_column(String(180), index=True)
    source_record_id: Mapped[str] = mapped_column(String(180), index=True)
    booking_date: Mapped[date] = mapped_column(Date, index=True)
    value_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    currency: Mapped[str] = mapped_column(String(3), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(24, 6))
    credit_debit: Mapped[str] = mapped_column(String(8), index=True)
    counterparty: Mapped[str] = mapped_column(String(180), default="")
    reference: Mapped[str] = mapped_column(String(240), default="", index=True)
    status: Mapped[str] = mapped_column(String(30), default="BOOKED", index=True)
    payload_hash: Mapped[str] = mapped_column(String(64), index=True)
    ingested_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None), index=True)


class ERPJournalRecord(Base):
    __tablename__ = "erp_journal_records"
    __table_args__ = (UniqueConstraint("connector_code", "source_record_id", name="uq_erp_journal_source"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    connector_code: Mapped[str] = mapped_column(String(80), index=True)
    legal_entity_id: Mapped[int | None] = mapped_column(ForeignKey("legal_entities.id"), nullable=True, index=True)
    source_record_id: Mapped[str] = mapped_column(String(180), index=True)
    posting_date: Mapped[date] = mapped_column(Date, index=True)
    currency: Mapped[str] = mapped_column(String(3), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(24, 6))
    counterparty: Mapped[str] = mapped_column(String(180), default="")
    reference: Mapped[str] = mapped_column(String(240), default="", index=True)
    document_type: Mapped[str] = mapped_column(String(50), default="BANK_GL")
    payload_hash: Mapped[str] = mapped_column(String(64), index=True)
    ingested_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None), index=True)


class ReconciliationExceptionRecord(Base):
    __tablename__ = "reconciliation_exception_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    reconciliation_run_id: Mapped[int] = mapped_column(ForeignKey("reconciliation_runs.id"), index=True)
    bank_transaction_id: Mapped[int | None] = mapped_column(ForeignKey("bank_transaction_records.id"), nullable=True, index=True)
    erp_journal_id: Mapped[int | None] = mapped_column(ForeignKey("erp_journal_records.id"), nullable=True, index=True)
    exception_type: Mapped[str] = mapped_column(String(60), index=True)
    amount_difference: Mapped[Decimal] = mapped_column(Numeric(24, 6), default=0)
    detail: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(24), default="OPEN", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None), index=True)


# Production Phase 1 v2: shadow promotion, data-quality SLAs and parallel-run evidence
class SourceAuthorityPolicy(Base):
    __tablename__ = "source_authority_policies"
    __table_args__ = (UniqueConstraint("connector_code", "data_domain", name="uq_source_authority_policy"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    connector_code: Mapped[str] = mapped_column(String(80), index=True)
    data_domain: Mapped[str] = mapped_column(String(60), index=True)
    mode: Mapped[str] = mapped_column(String(20), default="SHADOW", index=True)  # SHADOW / ACTIVE / BLOCKED
    evidence: Mapped[str] = mapped_column(Text, default="")
    approved_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None), index=True)


class IntegrationShadowRecord(Base):
    __tablename__ = "integration_shadow_records"
    __table_args__ = (UniqueConstraint("connector_code", "data_domain", "source_record_id", "payload_hash", name="uq_integration_shadow_source_hash"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    connector_code: Mapped[str] = mapped_column(String(80), index=True)
    data_domain: Mapped[str] = mapped_column(String(60), index=True)
    source_record_id: Mapped[str] = mapped_column(String(180), index=True)
    mapped_internal_id: Mapped[int | None] = mapped_column(nullable=True, index=True)
    target_table: Mapped[str] = mapped_column(String(80), index=True)
    currency: Mapped[str | None] = mapped_column(String(3), nullable=True, index=True)
    amount: Mapped[Decimal | None] = mapped_column(Numeric(24, 6), nullable=True)
    as_of: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    payload_hash: Mapped[str] = mapped_column(String(64), index=True)
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    status: Mapped[str] = mapped_column(String(24), default="SHADOW", index=True)
    ingested_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None), index=True)


class DataQualitySLAResult(Base):
    __tablename__ = "data_quality_sla_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    connector_code: Mapped[str] = mapped_column(String(80), index=True)
    data_domain: Mapped[str] = mapped_column(String(60), index=True)
    as_of: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None), index=True)
    timeliness_score: Mapped[Decimal] = mapped_column(Numeric(8, 6), default=0)
    completeness_score: Mapped[Decimal] = mapped_column(Numeric(8, 6), default=0)
    validity_score: Mapped[Decimal] = mapped_column(Numeric(8, 6), default=0)
    uniqueness_score: Mapped[Decimal] = mapped_column(Numeric(8, 6), default=0)
    reconciliation_score: Mapped[Decimal] = mapped_column(Numeric(8, 6), default=0)
    overall_score: Mapped[Decimal] = mapped_column(Numeric(8, 6), default=0)
    status: Mapped[str] = mapped_column(String(20), default="WATCH", index=True)
    breaches_json: Mapped[str] = mapped_column(Text, default="[]")


class ParallelRunObservation(Base):
    __tablename__ = "parallel_run_observations"
    __table_args__ = (UniqueConstraint("connector_code", "data_domain", "observation_date", "metric_name", name="uq_parallel_run_observation"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    connector_code: Mapped[str] = mapped_column(String(80), index=True)
    data_domain: Mapped[str] = mapped_column(String(60), index=True)
    observation_date: Mapped[date] = mapped_column(Date, index=True)
    metric_name: Mapped[str] = mapped_column(String(100), index=True)
    incumbent_value: Mapped[Decimal] = mapped_column(Numeric(24, 6))
    platform_value: Mapped[Decimal] = mapped_column(Numeric(24, 6))
    absolute_difference: Mapped[Decimal] = mapped_column(Numeric(24, 6), default=0)
    percentage_difference: Mapped[Decimal] = mapped_column(Numeric(12, 8), default=0)
    tolerance_pct: Mapped[Decimal] = mapped_column(Numeric(12, 8), default=0)
    status: Mapped[str] = mapped_column(String(20), default="PASS", index=True)
    evidence: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None), index=True)
