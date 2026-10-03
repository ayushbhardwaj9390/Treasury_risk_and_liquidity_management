from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.integrations.iso20022 import parse_camt_cash_report
from app.models import (
    BankAccount,
    BankTransactionRecord,
    CashFlow,
    DataLineageRecord,
    EnterpriseConnectorProfile,
    ERPJournalRecord,
    ExternalReferenceMap,
    FXRate,
    IntegrationCertificationControl,
    IntegrationQuarantine,
    IntegrationRun,
    LegalEntity,
    MarketCurvePoint,
    MarketDataFeed,
    ReconciliationExceptionRecord,
    ReconciliationRun,
    SourceConnector,
    VolatilityQuote,
    SourceAuthorityPolicy,
    IntegrationShadowRecord,
    DataQualitySLAResult,
    ParallelRunObservation,
)
from app.schemas.treasury import (
    CanonicalBankBatchIn,
    CanonicalBankTransactionBatchIn,
    CanonicalERPBatchIn,
    CanonicalERPJournalBatchIn,
    CanonicalMarketBatchIn,
    CanonicalMarketRiskBatchIn,
    DataLineageOut,
    DetailedReconciliationOut,
    ExternalMappingCreate,
    ExternalMappingRow,
    IntegrationCertificationRow,
    IntegrationCertificationUpdate,
    RealDataCoverageOut,
    SourceAuthorityUpdate,
    SourceAuthorityOut,
    ShadowRecordOut,
    DataQualitySLAOut,
    ParallelRunObservationIn,
    ParallelRunObservationOut,
    ParallelRunSummaryOut,
    ParallelReadinessOut,
    IntegrationIngestionOut,
    IntegrationRunOut,
    ISO20022BankStatementIn,
    ISO20022IngestionOut,
    ProductionPhase1StatusOut,
    QuarantineOut,
    ReconciliationExceptionOut,
)

ZERO = Decimal("0")
SUPPORTED_SCHEMA_VERSION = "1.0"


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _safe_json(value: Any) -> str:
    def default(obj: Any):
        if isinstance(obj, (Decimal, date, datetime)):
            return str(obj)
        raise TypeError(type(obj).__name__)

    return json.dumps(value, default=default, sort_keys=True, separators=(",", ":"))


def _hash(value: Any) -> str:
    return hashlib.sha256(_safe_json(value).encode()).hexdigest()


def _q(value: Decimal, quantum: str = "0.01") -> Decimal:
    return Decimal(value).quantize(Decimal(quantum))


def _ensure_source_connector(db: Session, connector_code: str, connector_type: str, source_system: str) -> SourceConnector:
    row = db.scalar(select(SourceConnector).where(SourceConnector.connector_name == connector_code))
    if row is None:
        row = SourceConnector(
            connector_name=connector_code,
            connector_type=connector_type,
            system_name=source_system,
            status="ACTIVE",
            last_success_at=_now(),
            stale_after_minutes=60,
            required_for_execution=connector_type in {"BANK", "ERP", "MARKET"},
            owner="TREASURY_TECH",
        )
        db.add(row)
        db.flush()
    return row


def _touch_profile(db: Session, connector_code: str, source_system: str, connector_type: str, *, success: bool) -> None:
    row = db.scalar(select(EnterpriseConnectorProfile).where(EnterpriseConnectorProfile.connector_code == connector_code))
    if row is None:
        row = EnterpriseConnectorProfile(
            connector_code=connector_code,
            connector_type=connector_type,
            system_name=source_system,
            protocol="CANONICAL_API",
            auth_mode="WORKLOAD_IDENTITY",
            environment=settings.environment.upper(),
            status="HEALTHY" if success else "DEGRADED",
            last_success_at=_now() if success else None,
            error_rate=ZERO if success else Decimal("1"),
            supports_idempotency=True,
            supports_reconciliation=True,
            data_contract_version=SUPPORTED_SCHEMA_VERSION,
        )
        db.add(row)
    else:
        if success:
            row.status = "HEALTHY"
            row.last_success_at = _now()
            row.error_rate = ZERO
        else:
            row.status = "DEGRADED"
            row.error_rate = max(Decimal(row.error_rate), Decimal("0.05"))


def _start_run(db: Session, connector_code: str, run_type: str, received: int, watermark: str | None, payload_hash: str) -> IntegrationRun:
    row = IntegrationRun(
        connector_code=connector_code,
        run_type=run_type,
        status="STARTED",
        records_received=received,
        watermark=watermark,
        payload_hash=payload_hash,
    )
    db.add(row)
    db.flush()
    return row


def _finish_run(
    db: Session,
    run: IntegrationRun,
    *,
    applied: int,
    quarantined: int,
    source_total: Decimal,
    target_total: Decimal,
    error_detail: str = "",
) -> IntegrationIngestionOut:
    run.records_applied = applied
    run.records_quarantined = quarantined
    run.source_total = source_total
    run.target_total = target_total
    run.difference = source_total - target_total
    run.status = "SUCCESS" if quarantined == 0 and not error_detail else "PARTIAL" if applied else "FAILED"
    run.error_detail = error_detail
    run.completed_at = _now()
    db.flush()
    return IntegrationIngestionOut(
        run_id=run.id,
        connector_code=run.connector_code,
        status=run.status,
        received=run.records_received,
        applied=applied,
        quarantined=quarantined,
        source_total=_q(source_total),
        target_total=_q(target_total),
        difference=_q(source_total - target_total),
        warnings=[] if quarantined == 0 else [f"{quarantined} record(s) quarantined; review /integrations/phase1/quarantine."],
    )


def _quarantine(db: Session, connector_code: str, record_type: str, source_reference: str, reason_code: str, reason_detail: str, payload: Any) -> None:
    db.add(IntegrationQuarantine(
        connector_code=connector_code,
        record_type=record_type,
        source_reference=source_reference,
        reason_code=reason_code,
        reason_detail=reason_detail,
        payload_json=_safe_json(payload),
    ))


def _lineage_exists(db: Session, connector_code: str, source_object_type: str, source_record_id: str, payload_hash: str) -> bool:
    return db.scalar(select(DataLineageRecord.id).where(
        DataLineageRecord.connector_code == connector_code,
        DataLineageRecord.source_object_type == source_object_type,
        DataLineageRecord.source_record_id == source_record_id,
        DataLineageRecord.payload_hash == payload_hash,
    ).limit(1)) is not None


def _lineage(
    db: Session,
    *,
    connector_code: str,
    source_system: str,
    source_object_type: str,
    source_record_id: str,
    target_table: str,
    target_record_id: int | None,
    source_timestamp: datetime | None,
    payload_hash: str,
    schema_version: str,
    reconciliation_status: str = "PENDING",
) -> None:
    if _lineage_exists(db, connector_code, source_object_type, source_record_id, payload_hash):
        return
    db.add(DataLineageRecord(
        connector_code=connector_code,
        source_system=source_system,
        source_object_type=source_object_type,
        source_record_id=source_record_id,
        target_table=target_table,
        target_record_id=target_record_id,
        source_timestamp=source_timestamp,
        payload_hash=payload_hash,
        schema_version=schema_version,
        reconciliation_status=reconciliation_status,
    ))


def _mapping(db: Session, connector_code: str, object_type: str, external_id: str) -> ExternalReferenceMap | None:
    return db.scalar(select(ExternalReferenceMap).where(
        ExternalReferenceMap.connector_code == connector_code,
        ExternalReferenceMap.object_type == object_type,
        ExternalReferenceMap.external_id == external_id,
        ExternalReferenceMap.active.is_(True),
    ))


def _authority_policy(db: Session, connector_code: str, data_domain: str) -> SourceAuthorityPolicy | None:
    return db.scalar(select(SourceAuthorityPolicy).where(
        SourceAuthorityPolicy.connector_code == connector_code,
        SourceAuthorityPolicy.data_domain == data_domain,
    ))


def _authority_mode(db: Session, connector_code: str, data_domain: str) -> str:
    row = _authority_policy(db, connector_code, data_domain)
    return row.mode.upper() if row else "SHADOW"


def _write_shadow_record(
    db: Session, *, connector_code: str, data_domain: str, source_record_id: str,
    mapped_internal_id: int | None, target_table: str, currency: str | None,
    amount: Decimal | None, as_of: datetime | None, payload_hash: str, payload: Any,
) -> IntegrationShadowRecord:
    existing = db.scalar(select(IntegrationShadowRecord).where(
        IntegrationShadowRecord.connector_code == connector_code,
        IntegrationShadowRecord.data_domain == data_domain,
        IntegrationShadowRecord.source_record_id == source_record_id,
        IntegrationShadowRecord.payload_hash == payload_hash,
    ))
    if existing:
        return existing
    row = IntegrationShadowRecord(
        connector_code=connector_code, data_domain=data_domain, source_record_id=source_record_id,
        mapped_internal_id=mapped_internal_id, target_table=target_table,
        currency=currency.upper() if currency else None, amount=amount, as_of=as_of,
        payload_hash=payload_hash, payload_json=_safe_json(payload), status="SHADOW",
    )
    db.add(row); db.flush()
    return row


def _authority_warning(mode: str, connector_code: str, data_domain: str) -> str | None:
    if mode == "SHADOW":
        return f"{connector_code}/{data_domain} accepted in SHADOW mode; authoritative treasury tables were not changed."
    if mode == "BLOCKED":
        return f"{connector_code}/{data_domain} is BLOCKED and cannot update authoritative treasury data."
    return None


def create_external_mapping(db: Session, request: ExternalMappingCreate) -> ExternalMappingRow:
    existing = _mapping(db, request.connector_code, request.object_type.upper(), request.external_id)
    if existing:
        existing.internal_id = request.internal_id
        existing.internal_code = request.internal_code
        existing.active = True
        row = existing
    else:
        row = ExternalReferenceMap(
            connector_code=request.connector_code,
            object_type=request.object_type.upper(),
            external_id=request.external_id,
            internal_id=request.internal_id,
            internal_code=request.internal_code,
        )
        db.add(row)
    db.commit()
    return ExternalMappingRow(
        connector_code=row.connector_code, object_type=row.object_type, external_id=row.external_id,
        internal_id=row.internal_id, internal_code=row.internal_code, active=row.active,
    )


def list_external_mappings(db: Session, connector_code: str | None = None) -> list[ExternalMappingRow]:
    stmt = select(ExternalReferenceMap).order_by(ExternalReferenceMap.connector_code, ExternalReferenceMap.object_type, ExternalReferenceMap.external_id)
    if connector_code:
        stmt = stmt.where(ExternalReferenceMap.connector_code == connector_code)
    return [ExternalMappingRow(
        connector_code=r.connector_code, object_type=r.object_type, external_id=r.external_id,
        internal_id=r.internal_id, internal_code=r.internal_code, active=r.active,
    ) for r in db.scalars(stmt).all()]


def ingest_bank_balances(db: Session, request: CanonicalBankBatchIn) -> IntegrationIngestionOut:
    payload_hash = _hash(request.model_dump())
    run = _start_run(db, request.connector_code, "BANK_BALANCE", len(request.balances), request.watermark, payload_hash)
    _ensure_source_connector(db, request.connector_code, "BANK", request.source_system)
    source_total = sum((Decimal(x.book_balance) for x in request.balances), ZERO)
    target_total = ZERO
    applied = quarantined = 0
    mode = _authority_mode(db, request.connector_code, "BANK_BALANCE")

    if request.schema_version != SUPPORTED_SCHEMA_VERSION:
        for x in request.balances:
            _quarantine(db, request.connector_code, "BANK_BALANCE", x.source_record_id, "UNSUPPORTED_SCHEMA", f"Expected {SUPPORTED_SCHEMA_VERSION}", x.model_dump())
        result = _finish_run(db, run, applied=0, quarantined=len(request.balances), source_total=source_total, target_total=ZERO, error_detail="Unsupported schema version")
        _touch_profile(db, request.connector_code, request.source_system, "BANK", success=False)
        db.commit()
        return result

    for x in request.balances:
        h = _hash(x.model_dump())
        if _lineage_exists(db, request.connector_code, "BANK_BALANCE", x.source_record_id, h):
            target_total += Decimal(x.book_balance); applied += 1; continue
        mapping = _mapping(db, request.connector_code, "BANK_ACCOUNT", x.external_account_id)
        account = db.get(BankAccount, mapping.internal_id) if mapping and mapping.internal_id else None
        if account is None:
            quarantined += 1
            _quarantine(db, request.connector_code, "BANK_BALANCE", x.source_record_id, "UNMAPPED_BANK_ACCOUNT", f"No active BANK_ACCOUNT mapping for {x.external_account_id}", x.model_dump())
            continue
        if account.currency.upper() != x.currency.upper():
            quarantined += 1
            _quarantine(db, request.connector_code, "BANK_BALANCE", x.source_record_id, "CURRENCY_MISMATCH", f"Mapped account currency {account.currency} != source {x.currency}", x.model_dump())
            continue
        if mode == "BLOCKED":
            quarantined += 1
            _quarantine(db, request.connector_code, "BANK_BALANCE", x.source_record_id, "SOURCE_AUTHORITY_BLOCKED", "Source authority policy blocks this domain", x.model_dump())
            continue
        as_of = x.as_of.replace(tzinfo=None) if x.as_of.tzinfo else x.as_of
        if mode == "SHADOW":
            shadow = _write_shadow_record(
                db, connector_code=request.connector_code, data_domain="BANK_BALANCE", source_record_id=x.source_record_id,
                mapped_internal_id=account.id, target_table="bank_accounts", currency=x.currency, amount=Decimal(x.book_balance),
                as_of=as_of, payload_hash=h, payload=x.model_dump(),
            )
            _lineage(db, connector_code=request.connector_code, source_system=request.source_system, source_object_type="BANK_BALANCE",
                     source_record_id=x.source_record_id, target_table="integration_shadow_records", target_record_id=shadow.id,
                     source_timestamp=as_of, payload_hash=h, schema_version=request.schema_version, reconciliation_status="SHADOW")
            target_total += Decimal(x.book_balance); applied += 1; continue

        account.book_balance = x.book_balance
        if x.restricted_balance is not None:
            account.restricted_balance = max(ZERO, Decimal(x.restricted_balance))
        elif x.available_balance is not None and Decimal(x.book_balance) >= ZERO:
            account.restricted_balance = max(ZERO, Decimal(x.book_balance) - Decimal(x.available_balance))
        account.last_updated = as_of
        db.flush()
        _lineage(db, connector_code=request.connector_code, source_system=request.source_system, source_object_type="BANK_BALANCE",
                 source_record_id=x.source_record_id, target_table="bank_accounts", target_record_id=account.id,
                 source_timestamp=account.last_updated, payload_hash=h, schema_version=request.schema_version, reconciliation_status="MATCHED")
        target_total += Decimal(account.book_balance); applied += 1

    connector = _ensure_source_connector(db, request.connector_code, "BANK", request.source_system)
    db.add(ReconciliationRun(
        connector_id=connector.id, run_type="BANK_BALANCE_IMPORT" if mode == "ACTIVE" else "BANK_BALANCE_IMPORT_SHADOW",
        source_total=source_total, target_total=target_total, difference=source_total-target_total, unmatched_count=quarantined,
        status="PASS" if quarantined == 0 and source_total == target_total else "REVIEW",
    ))
    result = _finish_run(db, run, applied=applied, quarantined=quarantined, source_total=source_total, target_total=target_total)
    warning = _authority_warning(mode, request.connector_code, "BANK_BALANCE")
    if warning: result.warnings.append(warning)
    _touch_profile(db, request.connector_code, request.source_system, "BANK", success=applied > 0 and quarantined == 0)
    db.commit()
    return result


def ingest_bank_transactions(db: Session, request: CanonicalBankTransactionBatchIn) -> IntegrationIngestionOut:
    payload_hash = _hash(request.model_dump())
    run = _start_run(db, request.connector_code, "BANK_TRANSACTION", len(request.transactions), request.watermark, payload_hash)
    _ensure_source_connector(db, request.connector_code, "BANK", request.source_system)
    source_total = sum((Decimal(x.amount) for x in request.transactions), ZERO)
    target_total = ZERO
    applied = quarantined = 0

    for x in request.transactions:
        h = _hash(x.model_dump())
        existing = db.scalar(select(BankTransactionRecord).where(
            BankTransactionRecord.connector_code == request.connector_code,
            BankTransactionRecord.source_record_id == x.source_record_id,
        ))
        if existing:
            if existing.payload_hash != h:
                quarantined += 1
                _quarantine(db, request.connector_code, "BANK_TRANSACTION", x.source_record_id, "IDEMPOTENCY_COLLISION", "Same source_record_id arrived with different payload", x.model_dump())
                continue
            target_total += Decimal(existing.amount)
            applied += 1
            continue
        mapping = _mapping(db, request.connector_code, "BANK_ACCOUNT", x.external_account_id)
        account = db.get(BankAccount, mapping.internal_id) if mapping and mapping.internal_id else None
        if account is None:
            quarantined += 1
            _quarantine(db, request.connector_code, "BANK_TRANSACTION", x.source_record_id, "UNMAPPED_BANK_ACCOUNT", f"No active BANK_ACCOUNT mapping for {x.external_account_id}", x.model_dump())
            continue
        if account.currency.upper() != x.currency.upper():
            quarantined += 1
            _quarantine(db, request.connector_code, "BANK_TRANSACTION", x.source_record_id, "CURRENCY_MISMATCH", f"Mapped account currency {account.currency} != source {x.currency}", x.model_dump())
            continue
        row = BankTransactionRecord(
            connector_code=request.connector_code, bank_account_id=account.id, external_account_id=x.external_account_id,
            source_record_id=x.source_record_id, booking_date=x.booking_date, value_date=x.value_date, currency=x.currency.upper(),
            amount=x.amount, credit_debit=x.credit_debit.upper(), counterparty=x.counterparty, reference=x.reference,
            status=x.status, payload_hash=h,
        )
        db.add(row); db.flush()
        _lineage(
            db, connector_code=request.connector_code, source_system=request.source_system, source_object_type="BANK_TRANSACTION",
            source_record_id=x.source_record_id, target_table="bank_transaction_records", target_record_id=row.id,
            source_timestamp=datetime.combine(x.booking_date, datetime.min.time()), payload_hash=h, schema_version=request.schema_version,
        )
        target_total += Decimal(row.amount); applied += 1

    result = _finish_run(db, run, applied=applied, quarantined=quarantined, source_total=source_total, target_total=target_total)
    _touch_profile(db, request.connector_code, request.source_system, "BANK", success=applied > 0 and quarantined == 0)
    db.commit()
    return result


def ingest_erp_flows(db: Session, request: CanonicalERPBatchIn) -> IntegrationIngestionOut:
    payload_hash = _hash(request.model_dump())
    run = _start_run(db, request.connector_code, "ERP_CASH_FLOW", len(request.flows), request.watermark, payload_hash)
    _ensure_source_connector(db, request.connector_code, "ERP", request.source_system)
    source_total = sum((Decimal(x.amount) for x in request.flows), ZERO)
    target_total = ZERO
    applied = quarantined = 0
    mode = _authority_mode(db, request.connector_code, "ERP_CASH_FLOW")

    for x in request.flows:
        h = _hash(x.model_dump())
        if x.flow_type.upper() not in {"RECEIVABLE", "PAYABLE"} or x.probability < 0 or x.probability > 1 or x.amount < 0:
            quarantined += 1
            _quarantine(db, request.connector_code, "ERP_CASH_FLOW", x.external_reference, "INVALID_FINANCIAL_FIELDS", "flow_type, amount or probability invalid", x.model_dump())
            continue
        mapping = _mapping(db, request.connector_code, "LEGAL_ENTITY", x.legal_entity_code)
        entity = db.get(LegalEntity, mapping.internal_id) if mapping and mapping.internal_id else None
        if entity is None:
            quarantined += 1
            _quarantine(db, request.connector_code, "ERP_CASH_FLOW", x.external_reference, "UNMAPPED_LEGAL_ENTITY", f"No active LEGAL_ENTITY mapping for {x.legal_entity_code}", x.model_dump())
            continue
        if mode == "BLOCKED":
            quarantined += 1
            _quarantine(db, request.connector_code, "ERP_CASH_FLOW", x.external_reference, "SOURCE_AUTHORITY_BLOCKED", "Source authority policy blocks this domain", x.model_dump())
            continue
        source_ts = x.source_timestamp.replace(tzinfo=None) if x.source_timestamp and x.source_timestamp.tzinfo else x.source_timestamp
        if mode == "SHADOW":
            shadow = _write_shadow_record(
                db, connector_code=request.connector_code, data_domain="ERP_CASH_FLOW", source_record_id=x.external_reference,
                mapped_internal_id=entity.id, target_table="cash_flows", currency=x.currency, amount=Decimal(x.amount),
                as_of=source_ts, payload_hash=h, payload=x.model_dump(),
            )
            _lineage(db, connector_code=request.connector_code, source_system=request.source_system, source_object_type="ERP_CASH_FLOW",
                     source_record_id=x.external_reference, target_table="integration_shadow_records", target_record_id=shadow.id,
                     source_timestamp=source_ts, payload_hash=h, schema_version=request.schema_version, reconciliation_status="SHADOW")
            target_total += Decimal(x.amount); applied += 1; continue

        source_ref = f"{request.connector_code}:{x.external_reference}"
        row = db.scalar(select(CashFlow).where(CashFlow.source_reference == source_ref))
        if row is None:
            row = CashFlow(source_reference=source_ref, entity_id=entity.id, flow_type=x.flow_type.upper(), counterparty=x.counterparty,
                           currency=x.currency.upper(), amount=x.amount, due_date=x.due_date, probability=x.probability, status=x.status)
            db.add(row)
        else:
            row.entity_id=entity.id; row.flow_type=x.flow_type.upper(); row.counterparty=x.counterparty; row.currency=x.currency.upper()
            row.amount=x.amount; row.due_date=x.due_date; row.probability=x.probability; row.status=x.status
        db.flush()
        _lineage(db, connector_code=request.connector_code, source_system=request.source_system, source_object_type="ERP_CASH_FLOW",
                 source_record_id=x.external_reference, target_table="cash_flows", target_record_id=row.id,
                 source_timestamp=source_ts, payload_hash=h, schema_version=request.schema_version)
        target_total += Decimal(row.amount); applied += 1

    result = _finish_run(db, run, applied=applied, quarantined=quarantined, source_total=source_total, target_total=target_total)
    warning = _authority_warning(mode, request.connector_code, "ERP_CASH_FLOW")
    if warning: result.warnings.append(warning)
    _touch_profile(db, request.connector_code, request.source_system, "ERP", success=applied > 0 and quarantined == 0)
    db.commit(); return result


def ingest_erp_journals(db: Session, request: CanonicalERPJournalBatchIn) -> IntegrationIngestionOut:
    payload_hash = _hash(request.model_dump())
    run = _start_run(db, request.connector_code, "ERP_JOURNAL", len(request.journals), request.watermark, payload_hash)
    _ensure_source_connector(db, request.connector_code, "ERP", request.source_system)
    source_total = sum((Decimal(x.amount) for x in request.journals), ZERO)
    target_total = ZERO
    applied = quarantined = 0
    for x in request.journals:
        h = _hash(x.model_dump())
        existing = db.scalar(select(ERPJournalRecord).where(
            ERPJournalRecord.connector_code == request.connector_code,
            ERPJournalRecord.source_record_id == x.source_record_id,
        ))
        if existing:
            if existing.payload_hash != h:
                quarantined += 1
                _quarantine(db, request.connector_code, "ERP_JOURNAL", x.source_record_id, "IDEMPOTENCY_COLLISION", "Same source_record_id arrived with different payload", x.model_dump())
                continue
            target_total += Decimal(existing.amount); applied += 1; continue
        mapping = _mapping(db, request.connector_code, "LEGAL_ENTITY", x.legal_entity_code)
        entity = db.get(LegalEntity, mapping.internal_id) if mapping and mapping.internal_id else None
        if entity is None:
            quarantined += 1
            _quarantine(db, request.connector_code, "ERP_JOURNAL", x.source_record_id, "UNMAPPED_LEGAL_ENTITY", f"No active LEGAL_ENTITY mapping for {x.legal_entity_code}", x.model_dump())
            continue
        row = ERPJournalRecord(
            connector_code=request.connector_code, legal_entity_id=entity.id, source_record_id=x.source_record_id,
            posting_date=x.posting_date, currency=x.currency.upper(), amount=x.amount, counterparty=x.counterparty,
            reference=x.reference, document_type=x.document_type, payload_hash=h,
        )
        db.add(row); db.flush()
        _lineage(
            db, connector_code=request.connector_code, source_system=request.source_system, source_object_type="ERP_JOURNAL",
            source_record_id=x.source_record_id, target_table="erp_journal_records", target_record_id=row.id,
            source_timestamp=datetime.combine(x.posting_date, datetime.min.time()), payload_hash=h, schema_version=request.schema_version,
        )
        target_total += Decimal(row.amount); applied += 1
    result = _finish_run(db, run, applied=applied, quarantined=quarantined, source_total=source_total, target_total=target_total)
    _touch_profile(db, request.connector_code, request.source_system, "ERP", success=applied > 0 and quarantined == 0)
    db.commit(); return result


def ingest_market_quotes(db: Session, request: CanonicalMarketBatchIn) -> IntegrationIngestionOut:
    payload_hash = _hash(request.model_dump())
    run = _start_run(db, request.connector_code, "MARKET_QUOTES", len(request.quotes), request.watermark, payload_hash)
    _ensure_source_connector(db, request.connector_code, "MARKET", request.source_system)
    source_total = sum((Decimal(x.mid) for x in request.quotes), ZERO)
    target_total = ZERO; applied = quarantined = 0
    mode = _authority_mode(db, request.connector_code, "MARKET_QUOTE")
    for x in request.quotes:
        h = _hash(x.model_dump())
        if x.asset_class.upper() != "FX" or not x.base_currency or not x.quote_currency or x.mid <= 0:
            quarantined += 1
            _quarantine(db, request.connector_code, "MARKET_QUOTE", x.source_record_id, "UNSUPPORTED_OR_INVALID_MARKET_QUOTE", "Phase-1 canonical quote endpoint accepts positive FX spot quotes; curves/volatility use /market-risk", x.model_dump())
            continue
        if _lineage_exists(db, request.connector_code, "MARKET_QUOTE", x.source_record_id, h):
            target_total += Decimal(x.mid); applied += 1; continue
        if mode == "BLOCKED":
            quarantined += 1
            _quarantine(db, request.connector_code, "MARKET_QUOTE", x.source_record_id, "SOURCE_AUTHORITY_BLOCKED", "Source authority policy blocks this domain", x.model_dump())
            continue
        as_of = x.as_of.replace(tzinfo=None) if x.as_of.tzinfo else x.as_of
        if mode == "SHADOW":
            shadow = _write_shadow_record(
                db, connector_code=request.connector_code, data_domain="MARKET_QUOTE", source_record_id=x.source_record_id,
                mapped_internal_id=None, target_table="fx_rates", currency=x.base_currency, amount=Decimal(x.mid),
                as_of=as_of, payload_hash=h, payload=x.model_dump(),
            )
            _lineage(db, connector_code=request.connector_code, source_system=request.source_system, source_object_type="MARKET_QUOTE",
                     source_record_id=x.source_record_id, target_table="integration_shadow_records", target_record_id=shadow.id,
                     source_timestamp=as_of, payload_hash=h, schema_version=request.schema_version, reconciliation_status="SHADOW")
            target_total += Decimal(x.mid); applied += 1; continue
        row = FXRate(base_currency=x.base_currency.upper(), quote_currency=x.quote_currency.upper(), rate=x.mid,
                     as_of=as_of, source=x.source)
        db.add(row); db.flush()
        _lineage(db, connector_code=request.connector_code, source_system=request.source_system, source_object_type="MARKET_QUOTE",
                 source_record_id=x.source_record_id, target_table="fx_rates", target_record_id=row.id, source_timestamp=row.as_of,
                 payload_hash=h, schema_version=request.schema_version, reconciliation_status="MATCHED")
        target_total += Decimal(row.rate); applied += 1
    feed = db.scalar(select(MarketDataFeed).where(MarketDataFeed.feed_name == request.connector_code))
    if feed is None:
        feed = MarketDataFeed(feed_name=request.connector_code, asset_class="FX", source_type="PRIMARY", status="ACTIVE" if mode == "ACTIVE" else "SHADOW",
                              last_received_at=_now(), stale_after_minutes=10, required_for_execution=True)
        db.add(feed)
    elif applied:
        feed.status="ACTIVE" if mode == "ACTIVE" else "SHADOW"; feed.last_received_at=_now()
    result=_finish_run(db, run, applied=applied, quarantined=quarantined, source_total=source_total, target_total=target_total)
    warning = _authority_warning(mode, request.connector_code, "MARKET_QUOTE")
    if warning: result.warnings.append(warning)
    _touch_profile(db, request.connector_code, request.source_system, "MARKET", success=applied > 0 and quarantined == 0)
    db.commit(); return result


def ingest_market_risk_data(db: Session, request: CanonicalMarketRiskBatchIn) -> IntegrationIngestionOut:
    count = len(request.curve_points) + len(request.volatility_quotes)
    payload_hash = _hash(request.model_dump())
    run = _start_run(db, request.connector_code, "MARKET_RISK_DATA", count, request.watermark, payload_hash)
    _ensure_source_connector(db, request.connector_code, "MARKET", request.source_system)
    source_total = ZERO; target_total = ZERO; applied = quarantined = 0
    curve_mode = _authority_mode(db, request.connector_code, "CURVE_POINT")
    vol_mode = _authority_mode(db, request.connector_code, "VOLATILITY_QUOTE")
    for x in request.curve_points:
        source_total += Decimal(x.zero_rate); h=_hash(x.model_dump())
        if x.tenor_days <= 0:
            quarantined += 1; _quarantine(db, request.connector_code, "CURVE_POINT", x.source_record_id, "INVALID_TENOR", "tenor_days must be positive", x.model_dump()); continue
        if _lineage_exists(db, request.connector_code, "CURVE_POINT", x.source_record_id, h):
            target_total += Decimal(x.zero_rate); applied += 1; continue
        if curve_mode == "BLOCKED":
            quarantined += 1; _quarantine(db, request.connector_code, "CURVE_POINT", x.source_record_id, "SOURCE_AUTHORITY_BLOCKED", "Source authority policy blocks this domain", x.model_dump()); continue
        as_of=x.as_of.replace(tzinfo=None) if x.as_of.tzinfo else x.as_of
        if curve_mode == "SHADOW":
            shadow=_write_shadow_record(db, connector_code=request.connector_code, data_domain="CURVE_POINT", source_record_id=x.source_record_id,
                mapped_internal_id=None, target_table="market_curve_points", currency=x.currency, amount=Decimal(x.zero_rate), as_of=as_of,
                payload_hash=h, payload=x.model_dump())
            _lineage(db, connector_code=request.connector_code, source_system=request.source_system, source_object_type="CURVE_POINT", source_record_id=x.source_record_id,
                target_table="integration_shadow_records", target_record_id=shadow.id, source_timestamp=as_of, payload_hash=h, schema_version=request.schema_version, reconciliation_status="SHADOW")
            target_total += Decimal(x.zero_rate); applied += 1; continue
        row=MarketCurvePoint(curve_name=x.curve_name, currency=x.currency.upper(), curve_type=x.curve_type.upper(), tenor_days=x.tenor_days,
                             zero_rate=x.zero_rate, as_of=as_of, source=x.source)
        db.add(row); db.flush()
        _lineage(db, connector_code=request.connector_code, source_system=request.source_system, source_object_type="CURVE_POINT", source_record_id=x.source_record_id,
                 target_table="market_curve_points", target_record_id=row.id, source_timestamp=row.as_of, payload_hash=h, schema_version=request.schema_version, reconciliation_status="MATCHED")
        target_total += Decimal(row.zero_rate); applied += 1
    for x in request.volatility_quotes:
        source_total += Decimal(x.volatility); h=_hash(x.model_dump())
        if x.tenor_days <= 0 or x.volatility <= 0:
            quarantined += 1; _quarantine(db, request.connector_code, "VOLATILITY_QUOTE", x.source_record_id, "INVALID_VOLATILITY", "tenor_days and volatility must be positive", x.model_dump()); continue
        if _lineage_exists(db, request.connector_code, "VOLATILITY_QUOTE", x.source_record_id, h):
            target_total += Decimal(x.volatility); applied += 1; continue
        if vol_mode == "BLOCKED":
            quarantined += 1; _quarantine(db, request.connector_code, "VOLATILITY_QUOTE", x.source_record_id, "SOURCE_AUTHORITY_BLOCKED", "Source authority policy blocks this domain", x.model_dump()); continue
        as_of=x.as_of.replace(tzinfo=None) if x.as_of.tzinfo else x.as_of
        if vol_mode == "SHADOW":
            shadow=_write_shadow_record(db, connector_code=request.connector_code, data_domain="VOLATILITY_QUOTE", source_record_id=x.source_record_id,
                mapped_internal_id=None, target_table="volatility_quotes", currency=None, amount=Decimal(x.volatility), as_of=as_of,
                payload_hash=h, payload=x.model_dump())
            _lineage(db, connector_code=request.connector_code, source_system=request.source_system, source_object_type="VOLATILITY_QUOTE", source_record_id=x.source_record_id,
                target_table="integration_shadow_records", target_record_id=shadow.id, source_timestamp=as_of, payload_hash=h, schema_version=request.schema_version, reconciliation_status="SHADOW")
            target_total += Decimal(x.volatility); applied += 1; continue
        row=VolatilityQuote(asset_class=x.asset_class.upper(), underlying=x.underlying.upper(), tenor_days=x.tenor_days, quote_type=x.quote_type.upper(),
                            volatility=x.volatility, as_of=as_of, source=x.source)
        db.add(row); db.flush()
        _lineage(db, connector_code=request.connector_code, source_system=request.source_system, source_object_type="VOLATILITY_QUOTE", source_record_id=x.source_record_id,
                 target_table="volatility_quotes", target_record_id=row.id, source_timestamp=row.as_of, payload_hash=h, schema_version=request.schema_version, reconciliation_status="MATCHED")
        target_total += Decimal(row.volatility); applied += 1
    result=_finish_run(db, run, applied=applied, quarantined=quarantined, source_total=source_total, target_total=target_total)
    for mode, domain in ((curve_mode, "CURVE_POINT"), (vol_mode, "VOLATILITY_QUOTE")):
        warning=_authority_warning(mode, request.connector_code, domain)
        if warning and warning not in result.warnings: result.warnings.append(warning)
    _touch_profile(db, request.connector_code, request.source_system, "MARKET", success=applied > 0 and quarantined == 0)
    db.commit(); return result


def ingest_iso20022_statement(db: Session, request: ISO20022BankStatementIn) -> ISO20022IngestionOut:
    parsed = parse_camt_cash_report(request.xml_payload)
    from app.schemas.treasury import CanonicalBankBalanceIn, CanonicalBankTransactionIn
    balance_batch = CanonicalBankBatchIn(
        connector_code=request.connector_code, source_system=request.source_system, schema_version=SUPPORTED_SCHEMA_VERSION,
        watermark=None,
        balances=[CanonicalBankBalanceIn(
            external_account_id=x.external_account_id, currency=x.currency, book_balance=x.book_balance,
            available_balance=x.available_balance, as_of=x.as_of, source_record_id=x.source_record_id,
        ) for x in parsed.balances],
    )
    transaction_batch = CanonicalBankTransactionBatchIn(
        connector_code=request.connector_code, source_system=request.source_system, schema_version=SUPPORTED_SCHEMA_VERSION,
        transactions=[CanonicalBankTransactionIn(
            external_account_id=x.external_account_id, source_record_id=x.source_record_id,
            booking_date=x.booking_date.date(), value_date=x.value_date.date() if x.value_date else None,
            currency=x.currency, amount=x.amount, credit_debit=x.credit_debit, counterparty=x.counterparty,
            reference=x.reference, status=x.status,
        ) for x in parsed.transactions],
    )
    balance_result = ingest_bank_balances(db, balance_batch) if balance_batch.balances else IntegrationIngestionOut(
        run_id=0, connector_code=request.connector_code, status="NO_BALANCES", received=0, applied=0, quarantined=0,
        source_total=ZERO, target_total=ZERO, difference=ZERO, warnings=[],
    )
    transaction_result = ingest_bank_transactions(db, transaction_batch) if transaction_batch.transactions else IntegrationIngestionOut(
        run_id=0, connector_code=request.connector_code, status="NO_TRANSACTIONS", received=0, applied=0, quarantined=0,
        source_total=ZERO, target_total=ZERO, difference=ZERO, warnings=[],
    )
    return ISO20022IngestionOut(message_type=parsed.message_type, balance_result=balance_result, transaction_result=transaction_result, warnings=parsed.warnings)


def run_bank_erp_reconciliation(
    db: Session,
    bank_connector_code: str,
    erp_connector_code: str,
    start_date: date,
    end_date: date,
    amount_tolerance: Decimal = Decimal("0.01"),
    date_tolerance_days: int = 2,
) -> DetailedReconciliationOut:
    if end_date < start_date:
        raise ValueError("end_date must be on or after start_date")
    bank = db.scalars(select(BankTransactionRecord).where(
        BankTransactionRecord.connector_code == bank_connector_code,
        BankTransactionRecord.booking_date >= start_date,
        BankTransactionRecord.booking_date <= end_date,
    ).order_by(BankTransactionRecord.booking_date, BankTransactionRecord.id)).all()
    erp = db.scalars(select(ERPJournalRecord).where(
        ERPJournalRecord.connector_code == erp_connector_code,
        ERPJournalRecord.posting_date >= start_date - timedelta(days=date_tolerance_days),
        ERPJournalRecord.posting_date <= end_date + timedelta(days=date_tolerance_days),
    ).order_by(ERPJournalRecord.posting_date, ERPJournalRecord.id)).all()

    source_connector = _ensure_source_connector(db, bank_connector_code, "BANK", bank_connector_code)
    source_total = sum((Decimal(x.amount) for x in bank), ZERO)
    target_total = sum((Decimal(x.amount) for x in erp), ZERO)
    run = ReconciliationRun(
        connector_id=source_connector.id, run_type="BANK_TO_ERP_DETAIL", source_total=source_total, target_total=target_total,
        difference=source_total-target_total, unmatched_count=0, status="RUNNING",
    )
    db.add(run); db.flush()

    remaining = {x.id: x for x in erp}
    matched_pairs: list[tuple[BankTransactionRecord, ERPJournalRecord]] = []
    unmatched_bank: list[BankTransactionRecord] = []
    for b in bank:
        candidates=[]
        for e in remaining.values():
            if b.currency != e.currency:
                continue
            diff=abs(Decimal(b.amount)-Decimal(e.amount))
            days=abs((b.booking_date-e.posting_date).days)
            if diff > amount_tolerance or days > date_tolerance_days:
                continue
            ref_match = bool(b.reference and e.reference and b.reference.strip().upper() == e.reference.strip().upper())
            cp_match = bool(b.counterparty and e.counterparty and b.counterparty.strip().upper() == e.counterparty.strip().upper())
            score=(100 if ref_match else 0)+(20 if cp_match else 0)-days-float(diff)
            candidates.append((score,e))
        if not candidates:
            unmatched_bank.append(b); continue
        candidates.sort(key=lambda x: (x[0], -x[1].id), reverse=True)
        best=candidates[0][1]
        matched_pairs.append((b,best)); remaining.pop(best.id,None)

    unmatched_erp=list(remaining.values())
    exceptions: list[ReconciliationExceptionRecord]=[]
    for b in unmatched_bank:
        ex=ReconciliationExceptionRecord(reconciliation_run_id=run.id, bank_transaction_id=b.id, exception_type="UNMATCHED_BANK_TRANSACTION",
                                         amount_difference=b.amount, detail=f"No ERP journal match within {date_tolerance_days} day(s) / {amount_tolerance} amount tolerance")
        db.add(ex); exceptions.append(ex)
    for e in unmatched_erp:
        ex=ReconciliationExceptionRecord(reconciliation_run_id=run.id, erp_journal_id=e.id, exception_type="UNMATCHED_ERP_JOURNAL",
                                         amount_difference=-Decimal(e.amount), detail=f"No bank transaction match within {date_tolerance_days} day(s) / {amount_tolerance} amount tolerance")
        db.add(ex); exceptions.append(ex)

    for b,e in matched_pairs:
        for connector,typ,ref in ((bank_connector_code,"BANK_TRANSACTION",b.source_record_id),(erp_connector_code,"ERP_JOURNAL",e.source_record_id)):
            rows=db.scalars(select(DataLineageRecord).where(DataLineageRecord.connector_code==connector,DataLineageRecord.source_object_type==typ,DataLineageRecord.source_record_id==ref)).all()
            for lin in rows: lin.reconciliation_status="MATCHED"
    for b in unmatched_bank:
        for lin in db.scalars(select(DataLineageRecord).where(DataLineageRecord.connector_code==bank_connector_code,DataLineageRecord.source_object_type=="BANK_TRANSACTION",DataLineageRecord.source_record_id==b.source_record_id)).all(): lin.reconciliation_status="EXCEPTION"
    for e in unmatched_erp:
        for lin in db.scalars(select(DataLineageRecord).where(DataLineageRecord.connector_code==erp_connector_code,DataLineageRecord.source_object_type=="ERP_JOURNAL",DataLineageRecord.source_record_id==e.source_record_id)).all(): lin.reconciliation_status="EXCEPTION"

    run.unmatched_count=len(exceptions)
    run.status="PASS" if not exceptions and abs(source_total-target_total)<=amount_tolerance else "REVIEW"
    db.flush()
    out_ex=[ReconciliationExceptionOut(id=x.id,reconciliation_run_id=run.id,bank_transaction_id=x.bank_transaction_id,erp_journal_id=x.erp_journal_id,
                                       exception_type=x.exception_type,amount_difference=Decimal(x.amount_difference),detail=x.detail,status=x.status) for x in exceptions]
    db.commit()
    return DetailedReconciliationOut(
        run_id=run.id,status=run.status,bank_transaction_count=len(bank),erp_journal_count=len(erp),matched_count=len(matched_pairs),
        unmatched_bank_count=len(unmatched_bank),unmatched_erp_count=len(unmatched_erp),source_total=_q(source_total),target_total=_q(target_total),
        difference=_q(source_total-target_total),exceptions=out_ex,
        warnings=[] if run.status=="PASS" else ["Reconciliation exceptions must be resolved before relying on affected balances/flows for execution-critical decisions."],
    )


def list_integration_runs(db: Session, limit: int = 50) -> list[IntegrationRunOut]:
    rows=db.scalars(select(IntegrationRun).order_by(IntegrationRun.started_at.desc()).limit(limit)).all()
    return [IntegrationRunOut.model_validate(r, from_attributes=True) for r in rows]


def list_lineage(db: Session, connector_code: str | None = None, limit: int = 100) -> list[DataLineageOut]:
    stmt=select(DataLineageRecord).order_by(DataLineageRecord.ingested_at.desc()).limit(limit)
    if connector_code: stmt=stmt.where(DataLineageRecord.connector_code==connector_code)
    rows=db.scalars(stmt).all()
    return [DataLineageOut.model_validate(r, from_attributes=True) for r in rows]


def list_quarantine(db: Session, open_only: bool = True, limit: int = 100) -> list[QuarantineOut]:
    stmt=select(IntegrationQuarantine).order_by(IntegrationQuarantine.quarantined_at.desc()).limit(limit)
    if open_only: stmt=stmt.where(IntegrationQuarantine.resolved.is_(False))
    rows=db.scalars(stmt).all()
    return [QuarantineOut.model_validate(r, from_attributes=True) for r in rows]


def production_phase1_status(db: Session) -> ProductionPhase1StatusOut:
    certs=db.scalars(select(IntegrationCertificationControl).order_by(IntegrationCertificationControl.connector_code,IntegrationCertificationControl.control_code)).all()
    profiles=db.scalars(select(EnterpriseConnectorProfile)).all()
    since=_now()-timedelta(hours=24)
    recent=db.scalars(select(IntegrationRun).where(IntegrationRun.started_at>=since)).all()
    stale_cutoff=_now()-timedelta(hours=24)
    pending=db.scalars(select(DataLineageRecord).where(DataLineageRecord.reconciliation_status=="PENDING",DataLineageRecord.ingested_at<stale_cutoff)).all()
    quarantine=db.scalars(select(IntegrationQuarantine).where(IntegrationQuarantine.resolved.is_(False))).all()
    required=[c for c in certs if c.required]
    passed=sum(1 for c in required if c.status=="PASS")
    overall="READY_FOR_LIVE_UAT" if required and passed==len(required) else "INTEGRATION_UAT" if any(c.status=="PASS" for c in required) else "BUILD"
    required_by_connector: dict[str, list[IntegrationCertificationControl]] = {}
    for control in required:
        required_by_connector.setdefault(control.connector_code, []).append(control)
    certified_connector_count = sum(
        1 for controls in required_by_connector.values()
        if controls and all(control.status == "PASS" for control in controls)
    )
    return ProductionPhase1StatusOut(
        phase="PRODUCTION_PHASE_1_REAL_DATA_INTEGRATION",overall_status=overall,integration_mode=getattr(settings,"integration_mode","sandbox"),
        live_connector_count=sum(1 for p in profiles if p.environment.upper()=="PRODUCTION" and p.status in {"HEALTHY","READY"}),
        certified_connector_count=certified_connector_count,
        recent_successful_runs=sum(1 for r in recent if r.status=="SUCCESS"),recent_failed_runs=sum(1 for r in recent if r.status=="FAILED"),
        open_quarantine_records=len(quarantine),stale_lineage_records=len(pending),
        certification=[IntegrationCertificationRow(connector_code=c.connector_code,control_code=c.control_code,required=c.required,status=c.status,evidence=c.evidence,owner=c.owner,last_checked_at=c.last_checked_at) for c in certs],
        warnings=[
            "Live provider credentials are not bundled with the project; production secrets must come from a managed secret provider.",
            "A connector is not production-certified until authentication, schema, reconciliation, idempotency, failover and volume tests have passed against the real provider.",
        ],
    )


def update_integration_certification(db: Session, connector_code: str, control_code: str, request: IntegrationCertificationUpdate, actor: str) -> IntegrationCertificationRow:
    allowed={"PASS","FAIL","WATCH","NOT_TESTED","BLOCKED"}
    status=request.status.upper()
    if status not in allowed:
        raise ValueError(f"Unsupported certification status {status}")
    row=db.scalar(select(IntegrationCertificationControl).where(
        IntegrationCertificationControl.connector_code==connector_code,
        IntegrationCertificationControl.control_code==control_code,
    ))
    if row is None:
        raise ValueError("Certification control not found")
    if status=="PASS" and not request.evidence.strip():
        raise ValueError("PASS requires evidence")
    row.status=status; row.evidence=request.evidence.strip(); row.last_checked_at=_now(); row.owner=actor
    db.commit()
    return IntegrationCertificationRow(connector_code=row.connector_code,control_code=row.control_code,required=row.required,status=row.status,evidence=row.evidence,owner=row.owner,last_checked_at=row.last_checked_at)


def real_data_coverage(db: Session) -> RealDataCoverageOut:
    report_ccy=settings.group_reporting_currency.upper()
    accounts=db.scalars(select(BankAccount)).all()
    open_flows=db.scalars(select(CashFlow).where(CashFlow.status=="OPEN")).all()
    active_bank_ids={x for x in db.scalars(select(DataLineageRecord.target_record_id).where(
        DataLineageRecord.target_table=="bank_accounts", DataLineageRecord.target_record_id.is_not(None),
        ~DataLineageRecord.source_system.like("%SYNTHETIC%"),
    )).all() if x is not None}
    shadow_bank_ids={x for x in db.scalars(select(IntegrationShadowRecord.mapped_internal_id).where(
        IntegrationShadowRecord.data_domain=="BANK_BALANCE", IntegrationShadowRecord.mapped_internal_id.is_not(None),
    )).all() if x is not None}
    bank_ids=active_bank_ids|shadow_bank_ids

    active_flow_ids={x for x in db.scalars(select(DataLineageRecord.target_record_id).where(
        DataLineageRecord.target_table=="cash_flows", DataLineageRecord.target_record_id.is_not(None),
        ~DataLineageRecord.source_system.like("%SYNTHETIC%"),
    )).all() if x is not None}
    shadow_flow_count=len(db.scalars(select(IntegrationShadowRecord.id).where(IntegrationShadowRecord.data_domain=="ERP_CASH_FLOW")).all())
    real_flow_count=min(len(open_flows), len(active_flow_ids & {f.id for f in open_flows}) + shadow_flow_count)

    currencies={x.currency.upper() for x in accounts}|{x.currency.upper() for x in open_flows}
    currencies.discard(report_ccy)
    fresh_cutoff=_now()-timedelta(hours=24)
    fresh_ccys=set()
    for ccy in currencies:
        active=db.scalar(select(FXRate.id).where(
            ((FXRate.base_currency==ccy)&(FXRate.quote_currency==report_ccy))|((FXRate.base_currency==report_ccy)&(FXRate.quote_currency==ccy)),
            FXRate.as_of>=fresh_cutoff, ~FXRate.source.like("%SYNTHETIC%"),
        ).limit(1))
        shadow=db.scalar(select(IntegrationShadowRecord.id).where(
            IntegrationShadowRecord.data_domain=="MARKET_QUOTE", IntegrationShadowRecord.currency==ccy,
            IntegrationShadowRecord.as_of>=fresh_cutoff,
        ).limit(1))
        if active is not None or shadow is not None: fresh_ccys.add(ccy)
    recs=db.scalars(select(ReconciliationRun).where(ReconciliationRun.run_type=="BANK_TO_ERP_DETAIL",ReconciliationRun.run_at>=_now()-timedelta(days=30))).all()
    passes=sum(1 for r in recs if r.status=="PASS")
    bank_cov=Decimal(len(bank_ids & {a.id for a in accounts}))/Decimal(len(accounts)) if accounts else Decimal("1")
    flow_cov=Decimal(real_flow_count)/Decimal(len(open_flows)) if open_flows else Decimal("1")
    market_cov=Decimal(len(fresh_ccys))/Decimal(len(currencies)) if currencies else Decimal("1")
    rec_rate=Decimal(passes)/Decimal(len(recs)) if recs else ZERO
    blockers=[]
    if bank_cov < Decimal("0.95"): blockers.append("Real-data bank-balance coverage is below 95%")
    if flow_cov < Decimal("0.90"): blockers.append("Real-data ERP cash-flow coverage is below 90%")
    if market_cov < Decimal("0.95"): blockers.append("Fresh real market-data currency coverage is below 95%")
    if rec_rate < Decimal("0.95"): blockers.append("30-day detailed bank-to-ERP reconciliation pass rate is below 95% or no qualifying runs exist")
    return RealDataCoverageOut(
        reporting_currency=report_ccy,overall_status="READY_FOR_PARALLEL_RUN" if not blockers else "UAT",
        bank_account_coverage_pct=_q(bank_cov,"0.0001"),erp_cashflow_coverage_pct=_q(flow_cov,"0.0001"),market_currency_coverage_pct=_q(market_cov,"0.0001"),
        reconciliation_pass_rate=_q(rec_rate,"0.0001"),bank_accounts_total=len(accounts),bank_accounts_real_data=len(bank_ids & {a.id for a in accounts}),
        open_cashflows_total=len(open_flows),open_cashflows_real_data=real_flow_count,required_market_currencies=len(currencies),fresh_market_currencies=len(fresh_ccys),
        reconciliation_runs=len(recs),reconciliation_passes=passes,blockers=blockers,
        warnings=["Coverage includes accepted SHADOW records so real-data completeness can be validated before authority promotion. It does not certify source-system completeness without provider/UAT evidence."],
    )


# --- Production Phase 1 v2: shadow promotion, data-quality SLA and parallel-run validation ---

def list_source_authorities(db: Session) -> list[SourceAuthorityOut]:
    rows = db.scalars(select(SourceAuthorityPolicy).order_by(SourceAuthorityPolicy.connector_code, SourceAuthorityPolicy.data_domain)).all()
    return [SourceAuthorityOut(
        connector_code=r.connector_code, data_domain=r.data_domain, mode=r.mode, evidence=r.evidence,
        approved_by=r.approved_by, approved_at=r.approved_at, updated_at=r.updated_at,
    ) for r in rows]


def list_shadow_records(db: Session, connector_code: str | None = None, data_domain: str | None = None, limit: int = 100) -> list[ShadowRecordOut]:
    stmt = select(IntegrationShadowRecord).order_by(IntegrationShadowRecord.ingested_at.desc()).limit(limit)
    if connector_code:
        stmt = stmt.where(IntegrationShadowRecord.connector_code == connector_code)
    if data_domain:
        stmt = stmt.where(IntegrationShadowRecord.data_domain == data_domain.upper())
    return [ShadowRecordOut.model_validate(r, from_attributes=True) for r in db.scalars(stmt).all()]


def record_parallel_run_observation(db: Session, request: ParallelRunObservationIn) -> ParallelRunObservationOut:
    if request.tolerance_pct < 0:
        raise ValueError("tolerance_pct must be non-negative")
    denom = abs(Decimal(request.incumbent_value))
    absolute = abs(Decimal(request.platform_value) - Decimal(request.incumbent_value))
    pct = absolute / denom if denom > ZERO else (ZERO if absolute == ZERO else Decimal("1"))
    status = "PASS" if pct <= Decimal(request.tolerance_pct) else "FAIL"
    row = db.scalar(select(ParallelRunObservation).where(
        ParallelRunObservation.connector_code == request.connector_code,
        ParallelRunObservation.data_domain == request.data_domain.upper(),
        ParallelRunObservation.observation_date == request.observation_date,
        ParallelRunObservation.metric_name == request.metric_name,
    ))
    if row is None:
        row = ParallelRunObservation(
            connector_code=request.connector_code, data_domain=request.data_domain.upper(), observation_date=request.observation_date,
            metric_name=request.metric_name, incumbent_value=request.incumbent_value, platform_value=request.platform_value,
            absolute_difference=absolute, percentage_difference=pct, tolerance_pct=request.tolerance_pct,
            status=status, evidence=request.evidence,
        )
        db.add(row)
    else:
        row.incumbent_value=request.incumbent_value; row.platform_value=request.platform_value
        row.absolute_difference=absolute; row.percentage_difference=pct; row.tolerance_pct=request.tolerance_pct
        row.status=status; row.evidence=request.evidence; row.created_at=_now()
    db.commit(); db.refresh(row)
    return ParallelRunObservationOut(
        id=row.id, connector_code=row.connector_code, data_domain=row.data_domain, observation_date=row.observation_date,
        metric_name=row.metric_name, incumbent_value=row.incumbent_value, platform_value=row.platform_value,
        absolute_difference=row.absolute_difference, percentage_difference=row.percentage_difference,
        tolerance_pct=row.tolerance_pct, status=row.status, evidence=row.evidence,
    )


def parallel_run_summary(db: Session, connector_code: str | None = None, data_domain: str | None = None, window_days: int = 30) -> ParallelRunSummaryOut:
    cutoff = date.today() - timedelta(days=window_days - 1)
    stmt = select(ParallelRunObservation).where(ParallelRunObservation.observation_date >= cutoff)
    if connector_code:
        stmt = stmt.where(ParallelRunObservation.connector_code == connector_code)
    if data_domain:
        stmt = stmt.where(ParallelRunObservation.data_domain == data_domain.upper())
    rows = list(db.scalars(stmt).all())
    count = len(rows); passed = sum(1 for r in rows if r.status == "PASS")
    days = len({r.observation_date for r in rows})
    pass_rate = Decimal(passed) / Decimal(count) if count else ZERO
    max_diff = max((Decimal(r.percentage_difference) for r in rows), default=ZERO)
    blockers: list[str] = []
    if days < 10: blockers.append("Fewer than 10 distinct parallel-run observation days are available")
    if pass_rate < Decimal("0.95"): blockers.append("Parallel-run pass rate is below 95%")
    if any(r.status == "FAIL" and Decimal(r.percentage_difference) > Decimal("0.02") for r in rows):
        blockers.append("At least one material parallel-run variance exceeds 2%")
    status = "READY" if not blockers else "UAT"
    return ParallelRunSummaryOut(
        connector_code=connector_code, data_domain=data_domain.upper() if data_domain else None, window_days=window_days,
        observation_count=count, distinct_observation_days=days, pass_count=passed,
        pass_rate=_q(pass_rate, "0.0001"), maximum_percentage_difference=_q(max_diff, "0.0001"),
        status=status, blockers=blockers,
        warnings=["Parallel-run evidence compares the platform with the incumbent source; it does not itself certify legal, tax or security readiness."],
    )


def evaluate_data_quality_sla(db: Session, connector_code: str, data_domain: str) -> DataQualitySLAOut:
    domain = data_domain.upper()
    run_type_map = {
        "BANK_BALANCE": "BANK_BALANCE", "BANK_TRANSACTION": "BANK_TRANSACTION", "ERP_CASH_FLOW": "ERP_CASH_FLOW",
        "ERP_JOURNAL": "ERP_JOURNAL", "MARKET_QUOTE": "MARKET_QUOTES", "CURVE_POINT": "MARKET_RISK_DATA",
        "VOLATILITY_QUOTE": "MARKET_RISK_DATA",
    }
    stale_minutes = {"BANK_BALANCE": 60, "BANK_TRANSACTION": 60, "ERP_CASH_FLOW": 1440, "ERP_JOURNAL": 1440,
                     "MARKET_QUOTE": 15, "CURVE_POINT": 60, "VOLATILITY_QUOTE": 60}.get(domain, 1440)
    run_type = run_type_map.get(domain, domain)
    since = _now() - timedelta(days=7)
    rows = list(db.scalars(select(IntegrationRun).where(
        IntegrationRun.connector_code == connector_code, IntegrationRun.run_type == run_type, IntegrationRun.started_at >= since,
    )).all())
    latest = max((r.completed_at or r.started_at for r in rows), default=None)
    timeliness = Decimal("1") if latest and (_now() - latest).total_seconds() <= stale_minutes * 60 else ZERO
    received = sum(r.records_received for r in rows); applied = sum(r.records_applied for r in rows); quarantined = sum(r.records_quarantined for r in rows)
    completeness = Decimal(applied) / Decimal(received) if received else ZERO
    validity = Decimal(max(received - quarantined, 0)) / Decimal(received) if received else ZERO
    collisions = len(db.scalars(select(IntegrationQuarantine).where(
        IntegrationQuarantine.connector_code == connector_code, IntegrationQuarantine.reason_code == "IDEMPOTENCY_COLLISION",
        IntegrationQuarantine.quarantined_at >= since,
    )).all())
    uniqueness = max(ZERO, Decimal("1") - (Decimal(collisions) / Decimal(received))) if received else ZERO
    if domain in {"BANK_TRANSACTION", "ERP_JOURNAL", "BANK_BALANCE", "ERP_CASH_FLOW"}:
        connector = db.scalar(select(SourceConnector).where(SourceConnector.connector_name == connector_code))
        recs = list(db.scalars(select(ReconciliationRun).where(
            ReconciliationRun.run_at >= since,
            ReconciliationRun.connector_id == connector.id if connector is not None else ReconciliationRun.connector_id == -1,
        )).all())
        reconciliation = Decimal(sum(1 for r in recs if r.status == "PASS")) / Decimal(len(recs)) if recs else ZERO
    else:
        matching = list(db.scalars(select(DataLineageRecord).where(
            DataLineageRecord.connector_code == connector_code, DataLineageRecord.source_object_type == domain,
            DataLineageRecord.ingested_at >= since,
        )).all())
        reconciliation = Decimal(sum(1 for r in matching if r.reconciliation_status in {"MATCHED", "SHADOW"})) / Decimal(len(matching)) if matching else ZERO
    scores = [timeliness, completeness, validity, uniqueness, reconciliation]
    overall = sum(scores, ZERO) / Decimal(len(scores))
    breaches=[]
    if timeliness < 1: breaches.append("TIMELINESS")
    if completeness < Decimal("0.98"): breaches.append("COMPLETENESS")
    if validity < Decimal("0.99"): breaches.append("VALIDITY")
    if uniqueness < Decimal("0.999"): breaches.append("UNIQUENESS")
    if reconciliation < Decimal("0.95"): breaches.append("RECONCILIATION")
    status = "PASS" if not breaches else "WATCH" if overall >= Decimal("0.90") else "FAIL"
    row = DataQualitySLAResult(
        connector_code=connector_code, data_domain=domain, as_of=_now(), timeliness_score=timeliness,
        completeness_score=completeness, validity_score=validity, uniqueness_score=uniqueness,
        reconciliation_score=reconciliation, overall_score=overall, status=status, breaches_json=_safe_json(breaches),
    )
    db.add(row); db.commit()
    return DataQualitySLAOut(
        connector_code=connector_code, data_domain=domain, as_of=row.as_of,
        timeliness_score=_q(timeliness,"0.0001"), completeness_score=_q(completeness,"0.0001"), validity_score=_q(validity,"0.0001"),
        uniqueness_score=_q(uniqueness,"0.0001"), reconciliation_score=_q(reconciliation,"0.0001"), overall_score=_q(overall,"0.0001"),
        status=status, breaches=breaches,
    )


def update_source_authority(db: Session, connector_code: str, data_domain: str, request: SourceAuthorityUpdate, actor: str) -> SourceAuthorityOut:
    mode = request.mode.upper(); domain = data_domain.upper()
    if mode not in {"SHADOW", "ACTIVE", "BLOCKED"}:
        raise ValueError("mode must be SHADOW, ACTIVE or BLOCKED")
    if mode == "ACTIVE":
        if not request.evidence.strip():
            raise ValueError("ACTIVE promotion requires evidence")
        required = list(db.scalars(select(IntegrationCertificationControl).where(
            IntegrationCertificationControl.connector_code == connector_code, IntegrationCertificationControl.required.is_(True),
        )).all())
        if not required or not all(r.status == "PASS" for r in required):
            raise ValueError("Connector cannot become ACTIVE until all required certification controls are PASS")
        latest_quality = db.scalar(select(DataQualitySLAResult).where(
            DataQualitySLAResult.connector_code == connector_code, DataQualitySLAResult.data_domain == domain,
        ).order_by(DataQualitySLAResult.as_of.desc()).limit(1))
        if latest_quality is None or latest_quality.status != "PASS":
            raise ValueError("Connector cannot become ACTIVE until the latest data-quality SLA result is PASS")
        parallel = parallel_run_summary(db, connector_code, domain, 30)
        if parallel.status != "READY":
            raise ValueError("Connector cannot become ACTIVE until the parallel-run gate is READY")
    row = _authority_policy(db, connector_code, domain)
    if row is None:
        row = SourceAuthorityPolicy(connector_code=connector_code, data_domain=domain)
        db.add(row)
    row.mode=mode; row.evidence=request.evidence.strip(); row.updated_at=_now()
    row.approved_by=actor if mode == "ACTIVE" else None; row.approved_at=_now() if mode == "ACTIVE" else None
    db.commit()
    return SourceAuthorityOut(connector_code=row.connector_code,data_domain=row.data_domain,mode=row.mode,evidence=row.evidence,
        approved_by=row.approved_by,approved_at=row.approved_at,updated_at=row.updated_at)


def resolve_quarantine_record(db: Session, quarantine_id: int, resolution: str, actor: str) -> QuarantineOut:
    row = db.get(IntegrationQuarantine, quarantine_id)
    if row is None:
        raise ValueError("Quarantine record not found")
    if not resolution.strip():
        raise ValueError("Resolution evidence is required")
    row.resolved=True; row.resolution=resolution.strip(); row.resolved_by=actor; row.resolved_at=_now()
    db.commit(); db.refresh(row)
    return QuarantineOut.model_validate(row, from_attributes=True)


def parallel_readiness(db: Session) -> ParallelReadinessOut:
    authorities = list(db.scalars(select(SourceAuthorityPolicy)).all())
    active=sum(1 for r in authorities if r.mode=="ACTIVE"); shadow=sum(1 for r in authorities if r.mode=="SHADOW"); blocked=sum(1 for r in authorities if r.mode=="BLOCKED")
    latest_quality: dict[tuple[str,str], DataQualitySLAResult] = {}
    for r in db.scalars(select(DataQualitySLAResult).order_by(DataQualitySLAResult.as_of.desc())).all():
        latest_quality.setdefault((r.connector_code,r.data_domain),r)
    quality_pass=sum(1 for r in latest_quality.values() if r.status=="PASS")
    parallel=parallel_run_summary(db, None, None, 30)
    coverage=real_data_coverage(db)
    blockers=[]
    if shadow: blockers.append(f"{shadow} source/domain authority policies remain in SHADOW mode")
    if blocked: blockers.append(f"{blocked} source/domain authority policies are BLOCKED")
    if parallel.status != "READY": blockers.extend(parallel.blockers)
    if coverage.overall_status != "READY_FOR_PARALLEL_RUN": blockers.extend(coverage.blockers)
    status="READY_FOR_CONTROLLED_PROMOTION" if not blockers and active else "PARALLEL_VALIDATION"
    return ParallelReadinessOut(status=status,active_authority_count=active,shadow_authority_count=shadow,blocked_authority_count=blocked,
        data_quality_pass_count=quality_pass,parallel_run_status=parallel.status,real_data_coverage_status=coverage.overall_status,
        blockers=list(dict.fromkeys(blockers)),warnings=["Authority promotion remains a human-controlled action and does not grant payment or trading execution rights."])
