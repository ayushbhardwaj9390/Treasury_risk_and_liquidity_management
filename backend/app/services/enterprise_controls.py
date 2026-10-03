from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import (
    ApprovalDecision,
    AuditLog,
    CreditFacility,
    HedgeAccountingDesignation,
    IntercompanyFacility,
    LegalEntity,
    MarketDataFeed,
    ReconciliationRun,
    SourceConnector,
    TransactionProposal,
    UserAccount,
    DerivativePosition,
    PaymentScreeningCase,
)
from app.schemas.treasury import (
    ApprovalDecisionOut,
    ConnectorStatusOut,
    ControlCheck,
    HedgeAccountingOut,
    MarketDataFeedStatus,
    ReconciliationOut,
    TransactionProposalCreate,
    TransactionProposalOut,
    UserAccessOut,
)
from app.services.exposure import calculate_fx_exposures
from app.services.fx import FXConversionError, convert
from app.services.global_treasury import calculate_cash_mobility, calculate_cross_border_funding
from app.services.advanced_intelligence import select_market_data_fallback

ZERO = Decimal("0")
MATERIAL_APPROVAL_THRESHOLD = Decimal("25000000")

ROLE_PERMISSIONS: dict[str, set[str]] = {
    "VIEWER": {"VIEW"},
    "TREASURY_ANALYST": {"VIEW", "CREATE_PROPOSAL"},
    "TREASURY_MANAGER": {"VIEW", "CREATE_PROPOSAL", "APPROVE_L1"},
    "GROUP_TREASURER": {"VIEW", "CREATE_PROPOSAL", "APPROVE_L1", "APPROVE_L2"},
    "RISK_MANAGER": {"VIEW", "RISK_REVIEW"},
    "PAYMENT_OPERATOR": {"VIEW", "RELEASE"},
    "AUDITOR": {"VIEW", "AUDIT"},
}


def _utc_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _age_minutes(ts: datetime | None) -> int:
    if ts is None:
        return 10**9
    return max(0, int((_utc_naive() - ts).total_seconds() // 60))


def _user(db: Session, username: str) -> UserAccount:
    user = db.scalar(select(UserAccount).where(UserAccount.username == username, UserAccount.active.is_(True)))
    if not user:
        raise PermissionError(f"Unknown or inactive user: {username}")
    return user


def require_permission(db: Session, username: str, permission: str) -> UserAccount:
    user = _user(db, username)
    if permission not in ROLE_PERMISSIONS.get(user.role, set()):
        raise PermissionError(f"{username} ({user.role}) lacks permission {permission}")
    return user


def list_user_access(db: Session) -> list[UserAccessOut]:
    users = db.scalars(select(UserAccount).where(UserAccount.active.is_(True)).order_by(UserAccount.username)).all()
    return [
        UserAccessOut(
            username=u.username,
            display_name=u.display_name,
            role=u.role,
            permissions=sorted(ROLE_PERMISSIONS.get(u.role, set())),
        )
        for u in users
    ]


def market_data_health(db: Session) -> list[MarketDataFeedStatus]:
    rows: list[MarketDataFeedStatus] = []
    for feed in db.scalars(select(MarketDataFeed).order_by(MarketDataFeed.asset_class, MarketDataFeed.feed_name)).all():
        age = _age_minutes(feed.last_received_at)
        stale = age > feed.stale_after_minutes
        execution_usable = feed.status == "ACTIVE" and not stale
        rows.append(MarketDataFeedStatus(
            feed_name=feed.feed_name,
            asset_class=feed.asset_class,
            source_type=feed.source_type,
            status=feed.status,
            age_minutes=age,
            stale_after_minutes=feed.stale_after_minutes,
            stale=stale,
            execution_usable=execution_usable,
        ))
    return rows


def connector_health(db: Session) -> list[ConnectorStatusOut]:
    rows: list[ConnectorStatusOut] = []
    for connector in db.scalars(select(SourceConnector).order_by(SourceConnector.connector_type, SourceConnector.connector_name)).all():
        age = _age_minutes(connector.last_success_at)
        stale = age > connector.stale_after_minutes
        execution_usable = connector.status == "ACTIVE" and not stale
        rows.append(ConnectorStatusOut(
            connector_name=connector.connector_name,
            connector_type=connector.connector_type,
            system_name=connector.system_name,
            status=connector.status,
            age_minutes=age,
            stale_after_minutes=connector.stale_after_minutes,
            stale=stale,
            execution_usable=execution_usable,
            owner=connector.owner,
        ))
    return rows


def latest_reconciliations(db: Session) -> list[ReconciliationOut]:
    connectors = {x.id: x for x in db.scalars(select(SourceConnector)).all()}
    runs = db.scalars(select(ReconciliationRun).order_by(ReconciliationRun.run_at.desc())).all()
    seen: set[tuple[int, str]] = set()
    out: list[ReconciliationOut] = []
    for run in runs:
        key = (run.connector_id, run.run_type)
        if key in seen:
            continue
        seen.add(key)
        connector = connectors.get(run.connector_id)
        out.append(ReconciliationOut(
            id=run.id,
            connector_name=connector.connector_name if connector else f"Connector {run.connector_id}",
            run_type=run.run_type,
            source_total=Decimal(run.source_total),
            target_total=Decimal(run.target_total),
            difference=Decimal(run.difference),
            unmatched_count=run.unmatched_count,
            status=run.status,
            run_at=run.run_at,
        ))
    return out


def hedge_accounting_status(db: Session) -> list[HedgeAccountingOut]:
    trades = {x.id: x for x in db.scalars(select(DerivativePosition)).all()}
    rows: list[HedgeAccountingOut] = []
    for d in db.scalars(select(HedgeAccountingDesignation).order_by(HedgeAccountingDesignation.id)).all():
        trade = trades.get(d.derivative_position_id)
        if not trade:
            continue
        control_status = "READY"
        if d.documentation_status != "COMPLETE":
            control_status = "DOCUMENTATION_GAP"
        elif d.effectiveness_status not in {"PASS", "EFFECTIVE"}:
            control_status = "EFFECTIVENESS_REVIEW"
        rows.append(HedgeAccountingOut(
            designation_id=d.id,
            derivative_position_id=d.derivative_position_id,
            instrument_type=trade.instrument_type,
            counterparty=trade.counterparty,
            designation_type=d.designation_type,
            hedged_item_reference=d.hedged_item_reference,
            risk_component=d.risk_component,
            hedge_ratio=Decimal(d.hedge_ratio),
            documentation_status=d.documentation_status,
            effectiveness_status=d.effectiveness_status,
            designation_date=d.designation_date,
            last_tested_at=d.last_tested_at,
            accounting_standard=d.accounting_standard,
            control_status=control_status,
        ))
    return rows


def _check(code: str, status: str, severity: str, message: str) -> ControlCheck:
    return ControlCheck(code=code, status=status, severity=severity, message=message)


def _entity(db: Session, entity_id: int | None) -> LegalEntity | None:
    return db.get(LegalEntity, entity_id) if entity_id else None


def _amount_reporting(db: Session, amount: Decimal, currency: str) -> Decimal:
    return convert(db, Decimal(amount), currency, settings.group_reporting_currency)


def _required_execution_data_checks(db: Session, proposal_type: str) -> list[ControlCheck]:
    checks: list[ControlCheck] = []
    required_connector_types = {"BANK", "ERP"}
    for c in connector_health(db):
        model = db.scalar(select(SourceConnector).where(SourceConnector.connector_name == c.connector_name))
        if not model or not model.required_for_execution or model.connector_type not in required_connector_types:
            continue
        if not c.execution_usable:
            checks.append(_check("CONNECTOR_FRESHNESS", "BLOCK", "HIGH", f"Required {model.connector_type} connector {c.connector_name} is stale or inactive."))

    if proposal_type == "FX_HEDGE":
        selected = select_market_data_fallback(db, "FX")
        if not selected.execution_usable:
            checks.append(_check("MARKET_DATA_FRESHNESS", "BLOCK", "HIGH", "No execution-usable approved FX market-data source is available."))
        elif selected.fallback_used:
            checks.append(_check("MARKET_DATA_FRESHNESS", "WARN", "MEDIUM", f"Approved fallback FX feed {selected.selected_feed} is being used because the primary feed is unavailable or stale."))
        else:
            checks.append(_check("MARKET_DATA_FRESHNESS", "PASS", "INFO", "Primary FX market data is within freshness tolerance."))
    return checks


def evaluate_proposal_controls(db: Session, proposal: TransactionProposal) -> list[ControlCheck]:
    checks: list[ControlCheck] = []
    ptype = proposal.proposal_type.upper()

    if Decimal(proposal.amount) <= ZERO:
        checks.append(_check("AMOUNT", "BLOCK", "HIGH", "Transaction amount must be positive."))
        return checks

    try:
        amount_reporting = _amount_reporting(db, Decimal(proposal.amount), proposal.currency)
        checks.append(_check("FX_CONVERSION", "PASS", "INFO", f"Amount converted to {settings.group_reporting_currency} {amount_reporting:.2f} for controls."))
    except FXConversionError as exc:
        checks.append(_check("FX_CONVERSION", "BLOCK", "HIGH", str(exc)))
        return checks

    checks.extend(_required_execution_data_checks(db, ptype))

    if proposal.counterparty:
        screening = db.scalar(select(PaymentScreeningCase).where(
            PaymentScreeningCase.counterparty == proposal.counterparty
        ).order_by(PaymentScreeningCase.screened_at.desc()).limit(1))
        if screening and screening.status in {"POTENTIAL_MATCH", "BLOCKED", "PENDING"}:
            checks.append(_check("PAYMENT_SCREENING", "BLOCK", "HIGH", f"Counterparty screening status is {screening.status}; compliance clearance is required before execution."))
        elif screening and screening.status == "CLEAR":
            checks.append(_check("PAYMENT_SCREENING", "PASS", "INFO", "Latest available counterparty screening result is CLEAR."))

    if ptype == "CASH_TRANSFER":
        if not proposal.source_entity_id or not proposal.target_entity_id:
            checks.append(_check("ENTITY_MAPPING", "BLOCK", "HIGH", "Cash transfer requires source and target legal entities."))
        else:
            mobility = calculate_cash_mobility(db)
            source = next((x for x in mobility.entities if x.entity_id == proposal.source_entity_id), None)
            if source is None:
                checks.append(_check("CASH_MOBILITY", "BLOCK", "HIGH", "Source entity is missing from cash-mobility analysis."))
            elif amount_reporting > Decimal(source.transferable_surplus_reporting):
                checks.append(_check("CASH_MOBILITY", "BLOCK", "HIGH", f"Transfer exceeds transferable surplus of {source.transferable_surplus_reporting:.2f} {settings.group_reporting_currency}."))
            else:
                checks.append(_check("CASH_MOBILITY", "PASS", "INFO", "Transfer remains within source entity transferable surplus."))

    elif ptype == "INTERCOMPANY_LOAN":
        if not proposal.source_entity_id or not proposal.target_entity_id:
            checks.append(_check("ENTITY_MAPPING", "BLOCK", "HIGH", "Intercompany loan requires lender and borrower entities."))
        else:
            facility = db.scalar(select(IntercompanyFacility).where(
                IntercompanyFacility.lender_entity_id == proposal.source_entity_id,
                IntercompanyFacility.borrower_entity_id == proposal.target_entity_id,
                IntercompanyFacility.currency == proposal.currency,
                IntercompanyFacility.status == "AVAILABLE",
            ))
            if not facility:
                checks.append(_check("INTERCOMPANY_FACILITY", "BLOCK", "HIGH", "No approved intercompany facility matches this route and currency."))
            else:
                available = Decimal(facility.limit_amount) - Decimal(facility.drawn_amount)
                if Decimal(proposal.amount) > available:
                    checks.append(_check("INTERCOMPANY_FACILITY", "BLOCK", "HIGH", f"Requested amount exceeds available intercompany capacity {available:.2f} {proposal.currency}."))
                else:
                    checks.append(_check("INTERCOMPANY_FACILITY", "PASS", "INFO", "Approved intercompany facility has sufficient capacity."))
                options = calculate_cross_border_funding(db)
                option = next((x for x in options if x.facility_id == facility.id), None)
                if option and option.transfer_pricing_status != "WITHIN_CONFIGURED_RANGE":
                    checks.append(_check("TRANSFER_PRICING", "BLOCK", "HIGH", f"Configured intercompany rate is {option.transfer_pricing_status}."))
                elif option:
                    checks.append(_check("TRANSFER_PRICING", "PASS", "INFO", "Intercompany rate is within configured arm's-length control range."))
                if option and option.tax_rule_status == "REVIEW_REQUIRED":
                    checks.append(_check("TAX_REVIEW", "BLOCK", "HIGH", "Applicable withholding-tax rule is marked REVIEW_REQUIRED. Cross-border funding cannot be released until an approved tax rule or tax-owner sign-off is recorded."))

    elif ptype == "FX_HEDGE":
        if not proposal.underlying_reference:
            checks.append(_check("HEDGE_MAPPING", "BLOCK", "HIGH", "FX hedge must reference an approved underlying exposure."))
        exposures = {x.currency: x for x in calculate_fx_exposures(db)}
        row = exposures.get(proposal.currency)
        if not row or abs(Decimal(row.residual_exposure)) == ZERO:
            checks.append(_check("HEDGE_CAPACITY", "BLOCK", "HIGH", f"No residual {proposal.currency} exposure is available to hedge."))
        elif Decimal(proposal.amount) > abs(Decimal(row.residual_exposure)):
            checks.append(_check("HEDGE_CAPACITY", "BLOCK", "HIGH", "Proposed hedge exceeds the current residual business exposure and could create a speculative position."))
        else:
            checks.append(_check("HEDGE_CAPACITY", "PASS", "INFO", "Proposed hedge is within current residual business exposure."))

    elif ptype == "FACILITY_DRAW":
        if not proposal.source_entity_id:
            checks.append(_check("ENTITY_MAPPING", "BLOCK", "HIGH", "Facility draw requires an entity."))
        else:
            q = select(CreditFacility).where(CreditFacility.entity_id == proposal.source_entity_id, CreditFacility.currency == proposal.currency, CreditFacility.committed.is_(True))
            if proposal.counterparty:
                q = q.where(CreditFacility.lender == proposal.counterparty)
            facility = db.scalar(q.limit(1))
            if not facility:
                checks.append(_check("FACILITY_CAPACITY", "BLOCK", "HIGH", "No matching committed credit facility was found."))
            else:
                available = Decimal(facility.limit_amount) - Decimal(facility.drawn_amount)
                status = "PASS" if Decimal(proposal.amount) <= available else "BLOCK"
                checks.append(_check("FACILITY_CAPACITY", status, "INFO" if status == "PASS" else "HIGH", f"Undrawn committed capacity is {available:.2f} {proposal.currency}."))
    else:
        checks.append(_check("PROPOSAL_TYPE", "BLOCK", "HIGH", f"Unsupported proposal type: {ptype}"))

    # Reconciliation warnings remain explicit. Required failed reconciliations block release.
    for r in latest_reconciliations(db):
        if r.status == "FAIL":
            checks.append(_check("RECONCILIATION", "BLOCK", "HIGH", f"{r.connector_name} {r.run_type} reconciliation failed with difference {r.difference}."))
        elif r.status == "WARN":
            checks.append(_check("RECONCILIATION", "WARN", "MEDIUM", f"{r.connector_name} {r.run_type} has {r.unmatched_count} unmatched items."))

    if not any(c.status == "BLOCK" for c in checks):
        checks.append(_check("PRE_TRADE_GATE", "PASS", "INFO", "No deterministic blocking control was identified."))
    return checks


def _serialize_checks(checks: list[ControlCheck]) -> str:
    return json.dumps([x.model_dump() for x in checks], separators=(",", ":"))


def _deserialize_checks(raw: str) -> list[ControlCheck]:
    try:
        return [ControlCheck(**x) for x in json.loads(raw or "[]")]
    except Exception:
        return []


def _proposal_out(db: Session, p: TransactionProposal) -> TransactionProposalOut:
    approvals = db.scalars(select(ApprovalDecision).where(ApprovalDecision.proposal_id == p.id).order_by(ApprovalDecision.created_at)).all()
    approve_count = sum(1 for x in approvals if x.decision == "APPROVE")
    try:
        amount_reporting = _amount_reporting(db, Decimal(p.amount), p.currency)
    except FXConversionError:
        amount_reporting = ZERO
    return TransactionProposalOut(
        id=p.id,
        proposal_type=p.proposal_type,
        source_entity_id=p.source_entity_id,
        target_entity_id=p.target_entity_id,
        counterparty=p.counterparty,
        currency=p.currency,
        amount=Decimal(p.amount),
        amount_reporting=amount_reporting,
        purpose=p.purpose,
        underlying_reference=p.underlying_reference,
        created_by=p.created_by,
        created_at=p.created_at,
        status=p.status,
        control_status=p.control_status,
        required_approvals=p.required_approvals,
        approval_count=approve_count,
        executed_at=p.executed_at,
        checks=_deserialize_checks(p.control_summary),
        approvals=[ApprovalDecisionOut(actor=x.actor, actor_role=x.actor_role, decision=x.decision, comment=x.comment, created_at=x.created_at) for x in approvals],
    )


def create_transaction_proposal(db: Session, request: TransactionProposalCreate, actor: str) -> TransactionProposalOut:
    require_permission(db, actor, "CREATE_PROPOSAL")
    p = TransactionProposal(
        proposal_type=request.proposal_type.upper(),
        source_entity_id=request.source_entity_id,
        target_entity_id=request.target_entity_id,
        counterparty=request.counterparty,
        currency=request.currency.upper(),
        amount=request.amount,
        purpose=request.purpose,
        underlying_reference=request.underlying_reference,
        created_by=actor,
        status="CONTROL_REVIEW",
    )
    db.add(p)
    db.flush()
    checks = evaluate_proposal_controls(db, p)
    blocked = any(c.status == "BLOCK" for c in checks)
    p.control_status = "BLOCKED" if blocked else ("WARNING" if any(c.status == "WARN" for c in checks) else "PASS")
    p.status = "CONTROL_FAILED" if blocked else "PENDING_APPROVAL"
    p.control_summary = _serialize_checks(checks)
    amount_reporting = _amount_reporting(db, Decimal(p.amount), p.currency)
    p.required_approvals = 2 if amount_reporting >= MATERIAL_APPROVAL_THRESHOLD else 1
    db.add(AuditLog(event_type="TRANSACTION_PROPOSAL_CREATED", actor=actor, details=f"proposal_id={p.id}; type={p.proposal_type}; amount={p.amount} {p.currency}; controls={p.control_status}"))
    db.commit()
    db.refresh(p)
    return _proposal_out(db, p)


def list_transaction_proposals(db: Session) -> list[TransactionProposalOut]:
    proposals = db.scalars(select(TransactionProposal).order_by(TransactionProposal.created_at.desc())).all()
    return [_proposal_out(db, p) for p in proposals]


def approve_transaction_proposal(db: Session, proposal_id: int, actor: str, decision: str, comment: str = "") -> TransactionProposalOut:
    user = require_permission(db, actor, "APPROVE_L1")
    p = db.get(TransactionProposal, proposal_id)
    if not p:
        raise ValueError("Proposal not found")
    if p.created_by == actor:
        raise PermissionError("Maker-checker violation: proposer cannot approve their own transaction")
    if p.status not in {"PENDING_APPROVAL", "PARTIALLY_APPROVED"}:
        raise ValueError(f"Proposal status {p.status} is not approvable")
    if p.control_status == "BLOCKED":
        raise ValueError("Blocked proposal cannot be approved")
    existing = db.scalar(select(ApprovalDecision).where(ApprovalDecision.proposal_id == p.id, ApprovalDecision.actor == actor))
    if existing:
        raise ValueError("Actor has already made an approval decision on this proposal")

    normalized = decision.upper()
    if normalized not in {"APPROVE", "REJECT"}:
        raise ValueError("Decision must be APPROVE or REJECT")
    db.add(ApprovalDecision(proposal_id=p.id, actor=actor, actor_role=user.role, decision=normalized, comment=comment))
    db.flush()

    if normalized == "REJECT":
        p.status = "REJECTED"
    else:
        approvals = db.scalars(select(ApprovalDecision).where(ApprovalDecision.proposal_id == p.id, ApprovalDecision.decision == "APPROVE")).all()
        roles = {x.actor_role for x in approvals}
        if len(approvals) >= p.required_approvals and (p.required_approvals == 1 or "GROUP_TREASURER" in roles):
            p.status = "APPROVED"
        else:
            p.status = "PARTIALLY_APPROVED"
    db.add(AuditLog(event_type="TRANSACTION_APPROVAL_DECISION", actor=actor, details=f"proposal_id={p.id}; decision={normalized}; status={p.status}"))
    db.commit()
    db.refresh(p)
    return _proposal_out(db, p)


def release_transaction_proposal(db: Session, proposal_id: int, actor: str) -> TransactionProposalOut:
    if settings.environment.lower() == "production":
        from app.services.production import require_live_release
        require_live_release(db)
    require_permission(db, actor, "RELEASE")
    p = db.get(TransactionProposal, proposal_id)
    if not p:
        raise ValueError("Proposal not found")
    if p.status != "APPROVED":
        raise ValueError("Only fully approved proposals can be released")
    if p.created_by == actor:
        raise PermissionError("Segregation-of-duties violation: maker cannot release transaction")
    prior = db.scalars(select(ApprovalDecision).where(ApprovalDecision.proposal_id == p.id, ApprovalDecision.decision == "APPROVE")).all()
    if actor in {x.actor for x in prior}:
        raise PermissionError("Segregation-of-duties violation: approver cannot release transaction")

    # Reperform controls immediately before release so stale feeds/reconciliations can stop execution.
    checks = evaluate_proposal_controls(db, p)
    p.control_summary = _serialize_checks(checks)
    if any(c.status == "BLOCK" for c in checks):
        p.control_status = "BLOCKED"
        db.add(AuditLog(event_type="TRANSACTION_RELEASE_BLOCKED", actor=actor, details=f"proposal_id={p.id}; deterministic controls failed on release"))
        db.commit()
        raise ValueError("Release blocked because deterministic pre-trade controls no longer pass")

    p.control_status = "WARNING" if any(c.status == "WARN" for c in checks) else "PASS"
    p.status = "RELEASED_FOR_EXECUTION"
    p.executed_at = _utc_naive()
    db.add(AuditLog(event_type="TRANSACTION_RELEASED", actor=actor, details=f"proposal_id={p.id}; released_to=external_execution_connector; no autonomous bank action performed"))
    db.commit()
    db.refresh(p)
    return _proposal_out(db, p)
