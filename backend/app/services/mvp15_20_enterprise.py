from __future__ import annotations

from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import (
    CashFlow,
    CrossBorderConstraint,
    DeploymentReadinessControl,
    EnterpriseConnectorProfile,
    InvestigationCase,
    LegalEntity,
    ModelRegistryEntry,
    ModelValidationRecord,
    SecurityControlRecord,
)
from app.schemas.treasury import (
    ConnectorReadinessOut,
    ConnectorReadinessRow,
    CrossBorderConstraintGraphOut,
    CrossBorderConstraintRow,
    EnterpriseSecurityControlRow,
    EnterpriseSecurityPostureOut,
    LegalEntityLiquidityOptimizationOut,
    LiquidityRouteProposal,
    ModelValidationDashboardOut,
    ModelValidationRow,
    ProductionReadinessOut,
    ProductionReadinessRow,
    RoleWorkspaceOut,
    RoleWorkQueueItem,
)
from app.services.global_treasury import calculate_cash_mobility
from app.services.fx import FXConversionError, convert

ZERO = Decimal("0")


def _q(v: Decimal | int | float, places: str = "0.01") -> Decimal:
    return Decimal(str(v)).quantize(Decimal(places))


def cross_border_constraint_graph(db: Session) -> CrossBorderConstraintGraphOut:
    rows = db.scalars(select(CrossBorderConstraint).order_by(CrossBorderConstraint.source_country, CrossBorderConstraint.target_country)).all()
    out: list[CrossBorderConstraintRow] = []
    executable_count = 0
    for row in rows:
        blockers: list[str] = []
        if row.regulatory_status != "APPROVED":
            blockers.append(f"Regulatory status is {row.regulatory_status}")
        if row.legal_status != "APPROVED":
            blockers.append(f"Legal status is {row.legal_status}")
        if row.requires_tax_review:
            blockers.append("Tax review required")
        if row.requires_legal_review:
            blockers.append("Legal review required")
        executable = not blockers
        executable_count += int(executable)
        out.append(CrossBorderConstraintRow(
            source_country=row.source_country,
            target_country=row.target_country,
            transfer_type=row.transfer_type,
            currency=row.currency,
            max_amount_reporting=None if row.max_amount_reporting is None else Decimal(row.max_amount_reporting),
            withholding_tax_rate=Decimal(row.withholding_tax_rate),
            regulatory_status=row.regulatory_status,
            legal_status=row.legal_status,
            executable=executable,
            blockers=blockers,
        ))
    return CrossBorderConstraintGraphOut(
        reporting_currency=settings.group_reporting_currency,
        active_route_count=len(out),
        executable_route_count=executable_count,
        blocked_route_count=len(out) - executable_count,
        rows=out,
        warnings=[
            "Cross-border routes are governed configuration, not legal or tax advice.",
            "A route becomes executable only after regulatory, legal and required tax reviews are cleared.",
        ],
    )


def optimize_legal_entity_liquidity(db: Session) -> LegalEntityLiquidityOptimizationOut:
    mobility = calculate_cash_mobility(db)
    entities = {e.id: e for e in db.scalars(select(LegalEntity)).all()}
    constraints = db.scalars(select(CrossBorderConstraint)).all()
    by_route: dict[tuple[str, str], list[CrossBorderConstraint]] = defaultdict(list)
    for c in constraints:
        by_route[(c.source_country, c.target_country)].append(c)

    # Optimize against a 90-day projected entity position rather than today's balance only.
    # This catches legal-entity timing gaps even when the group has ample headline cash.
    horizon = date.today() + timedelta(days=90)
    projected_net: dict[int, Decimal] = defaultdict(lambda: ZERO)
    flows = db.scalars(select(CashFlow).where(CashFlow.status == "OPEN", CashFlow.due_date <= horizon)).all()
    for flow in flows:
        try:
            amount = convert(db, Decimal(flow.amount), flow.currency, settings.group_reporting_currency)
        except FXConversionError:
            continue
        if flow.flow_type == "RECEIVABLE":
            projected_net[flow.entity_id] += amount * min(max(Decimal(flow.probability), ZERO), Decimal("1"))
        elif flow.flow_type == "PAYABLE":
            projected_net[flow.entity_id] -= amount

    projected_deficits: dict[int, Decimal] = {}
    for row in mobility.entities:
        projected_cash = Decimal(row.deployable_cash_reporting) + projected_net[row.entity_id]
        projected_deficits[row.entity_id] = max(Decimal(row.minimum_cash_reporting) - projected_cash, ZERO)

    sources = [x for x in mobility.entities if Decimal(x.transferable_surplus_reporting) > 0]
    deficits = [x for x in mobility.entities if projected_deficits[x.entity_id] > 0]
    source_remaining = {x.entity_id: Decimal(x.transferable_surplus_reporting) for x in sources}
    deficit_remaining = {x.entity_id: projected_deficits[x.entity_id] for x in deficits}
    routes: list[LiquidityRouteProposal] = []

    for deficit in sorted(deficits, key=lambda x: Decimal(x.local_cash_deficit_reporting), reverse=True):
        target_entity = entities[deficit.entity_id]
        for source in sorted(sources, key=lambda x: Decimal(x.transferable_surplus_reporting), reverse=True):
            if deficit_remaining[deficit.entity_id] <= 0:
                break
            available = source_remaining[source.entity_id]
            if available <= 0 or source.entity_id == deficit.entity_id:
                continue
            source_entity = entities[source.entity_id]
            candidates = by_route.get((source_entity.country_code, target_entity.country_code), [])
            approved = [c for c in candidates if c.regulatory_status == "APPROVED" and c.legal_status == "APPROVED" and not c.requires_tax_review and not c.requires_legal_review]
            chosen = approved[0] if approved else (candidates[0] if candidates else None)
            blockers: list[str] = []
            if chosen is None:
                blockers = ["No configured cross-border transfer route"]
                transfer_type = "UNCONFIGURED"
                cap = ZERO
                wht = ZERO
            else:
                transfer_type = chosen.transfer_type
                if chosen.regulatory_status != "APPROVED":
                    blockers.append(f"Regulatory status is {chosen.regulatory_status}")
                if chosen.legal_status != "APPROVED":
                    blockers.append(f"Legal status is {chosen.legal_status}")
                if chosen.requires_tax_review:
                    blockers.append("Tax review required")
                if chosen.requires_legal_review:
                    blockers.append("Legal review required")
                cap = Decimal(chosen.max_amount_reporting) if chosen.max_amount_reporting is not None else available
                wht = Decimal(chosen.withholding_tax_rate)
            amount = min(available, deficit_remaining[deficit.entity_id], max(cap, ZERO)) if not blockers else ZERO
            status = "PROPOSED" if amount > 0 else "BLOCKED"
            routes.append(LiquidityRouteProposal(
                source_entity=source_entity.name,
                target_entity=target_entity.name,
                source_country=source_entity.country_code,
                target_country=target_entity.country_code,
                transfer_type=transfer_type,
                currency=settings.group_reporting_currency,
                amount_reporting=_q(amount),
                estimated_withholding_cost=_q(amount * wht),
                status=status,
                blockers=blockers,
            ))
            if amount > 0:
                source_remaining[source.entity_id] -= amount
                deficit_remaining[deficit.entity_id] -= amount

    proposed = sum((Decimal(r.amount_reporting) for r in routes), ZERO)
    unresolved = sum(deficit_remaining.values(), ZERO)
    return LegalEntityLiquidityOptimizationOut(
        reporting_currency=settings.group_reporting_currency,
        transferable_surplus=_q(mobility.total_transferable_surplus),
        local_deficit=_q(sum(projected_deficits.values(), ZERO)),
        proposed_transfer=_q(proposed),
        unresolved_deficit=_q(unresolved),
        routes=routes,
        execution_authority="NONE",
        warnings=[
            "Optimizer uses a 90-day probability-weighted entity cash view and only configured, cleared routes; it never bypasses local minimum cash or mobility restrictions.",
            "Proposals require treasury, tax/legal review and the existing maker-checker execution workflow.",
        ],
    )


def enterprise_connector_readiness(db: Session) -> ConnectorReadinessOut:
    rows = db.scalars(select(EnterpriseConnectorProfile).order_by(EnterpriseConnectorProfile.connector_type, EnterpriseConnectorProfile.connector_code)).all()
    out: list[ConnectorReadinessRow] = []
    ready = degraded = blocked = 0
    now = datetime.now(UTC).replace(tzinfo=None)
    for c in rows:
        gaps: list[str] = []
        if c.status not in {"HEALTHY", "READY"}:
            gaps.append(f"Connector status is {c.status}")
        if c.last_success_at is None or (now - c.last_success_at).total_seconds() > 900:
            gaps.append("No successful data exchange within 15 minutes")
        if Decimal(c.error_rate) > Decimal("0.02"):
            gaps.append("Error rate exceeds 2%")
        if not c.supports_idempotency:
            gaps.append("Idempotency not supported")
        if not c.supports_reconciliation:
            gaps.append("Reconciliation contract not supported")
        readiness = "READY" if not gaps else "DEGRADED" if len(gaps) <= 2 else "BLOCKED"
        ready += int(readiness == "READY")
        degraded += int(readiness == "DEGRADED")
        blocked += int(readiness == "BLOCKED")
        out.append(ConnectorReadinessRow(
            connector_code=c.connector_code,
            connector_type=c.connector_type,
            system_name=c.system_name,
            environment=c.environment,
            status=c.status,
            last_success_at=c.last_success_at,
            latency_ms=None if c.latency_ms is None else Decimal(c.latency_ms),
            error_rate=Decimal(c.error_rate),
            supports_idempotency=c.supports_idempotency,
            supports_reconciliation=c.supports_reconciliation,
            readiness=readiness,
            gaps=gaps,
        ))
    return ConnectorReadinessOut(
        ready_count=ready,
        degraded_count=degraded,
        blocked_count=blocked,
        rows=out,
        canonical_contract_version="MVP16-1.0",
        warnings=["Demo connector profiles are architectural contracts; production adapters require provider certification, workload identity and reconciliation testing."],
    )


def enterprise_security_posture(db: Session) -> EnterpriseSecurityPostureOut:
    rows = db.scalars(select(SecurityControlRecord).order_by(SecurityControlRecord.domain, SecurityControlRecord.control_code)).all()
    now = datetime.now(UTC).replace(tzinfo=None)
    out: list[EnterpriseSecurityControlRow] = []
    required = passing = failing = 0
    for row in rows:
        age = None if row.last_tested_at is None else max(0, (now - row.last_tested_at).days)
        required += int(row.required)
        ok = row.status == "PASS"
        passing += int(row.required and ok)
        failing += int(row.required and not ok)
        out.append(EnterpriseSecurityControlRow(
            control_code=row.control_code,
            domain=row.domain,
            status=row.status,
            required=row.required,
            owner=row.owner,
            evidence=row.evidence,
            age_days=age,
        ))
    coverage = Decimal(passing) / Decimal(required) if required else ZERO
    overall = "PASS" if failing == 0 and required > 0 else "BLOCKED" if failing > 0 else "NOT_CONFIGURED"
    return EnterpriseSecurityPostureOut(
        environment=settings.environment,
        overall_status=overall,
        required_controls=required,
        passing_controls=passing,
        failing_controls=failing,
        coverage_pct=_q(coverage, "0.0001"),
        rows=out,
        warnings=[
            "Production treasury writes require federated identity, managed secrets/HSM-backed signing, SIEM telemetry and environment segregation.",
            "Security control evidence must be independently tested before production go-live.",
        ],
    )


def model_validation_dashboard(db: Session) -> ModelValidationDashboardOut:
    records = db.scalars(select(ModelValidationRecord).order_by(ModelValidationRecord.model_code, ModelValidationRecord.created_at.desc())).all()
    registry = db.scalars(select(ModelRegistryEntry)).all()
    out = [ModelValidationRow(
        model_code=r.model_code,
        validation_type=r.validation_type,
        metric_name=r.metric_name,
        metric_value=Decimal(r.metric_value),
        threshold_value=Decimal(r.threshold_value),
        comparison=r.comparison,
        status=r.status,
        validated_by=r.validated_by,
        created_at=r.created_at,
    ) for r in records]
    pass_count = sum(1 for r in records if r.status == "PASS")
    watch_count = sum(1 for r in records if r.status == "WATCH")
    fail_count = sum(1 for r in records if r.status == "FAIL")
    by_model: dict[str, list[ModelValidationRecord]] = defaultdict(list)
    for r in records:
        by_model[r.model_code].append(r)
    blocked = sorted({m.model_code for m in registry if m.validation_status not in {"VALIDATED", "PASS"}} | {code for code, vals in by_model.items() if any(v.status == "FAIL" for v in vals)})
    return ModelValidationDashboardOut(
        model_count=len(registry),
        validation_count=len(records),
        pass_count=pass_count,
        watch_count=watch_count,
        fail_count=fail_count,
        production_blocked_models=blocked,
        rows=out,
        warnings=[
            "Model promotion is never automatic; FAIL and unvalidated models remain blocked from production decision use.",
            "Backtesting and valuation validation require independently governed data and documented thresholds.",
        ],
    )


def role_workspace(db: Session, role: str) -> RoleWorkspaceOut:
    normalized = role.upper()
    allowed = {"CFO", "GROUP_TREASURER", "RISK", "TREASURY_OPERATIONS", "TAX", "AUDIT"}
    if normalized not in allowed:
        raise ValueError(f"Unsupported role. Use one of: {', '.join(sorted(allowed))}")
    cases = db.scalars(select(InvestigationCase).where(InvestigationCase.status != "CLOSED").order_by(InvestigationCase.opened_at.desc())).all()
    entities = {e.id: e.name for e in db.scalars(select(LegalEntity)).all()}
    visible = [c for c in cases if c.owner_role == normalized or normalized in {"CFO", "GROUP_TREASURER"}]
    queue = [RoleWorkQueueItem(
        reference=c.reference,
        case_type=c.case_type,
        title=c.title,
        severity=c.severity,
        status=c.status,
        owner_role=c.owner_role,
        entity_name=entities.get(c.entity_id) if c.entity_id else None,
        details=c.details,
    ) for c in visible]
    panels = {
        "CFO": ["Global liquidity", "Tail risk", "Funding concentration", "Capital allocation", "Decision pack"],
        "GROUP_TREASURER": ["Cash position", "Forecast", "Hedges", "Funding", "Approvals", "Counterparties"],
        "RISK": ["Limits", "Stress testing", "VaR/LaR", "Model validation", "Counterparty risk"],
        "TREASURY_OPERATIONS": ["Bank status", "Reconciliations", "Payments", "Intraday liquidity", "Exceptions"],
        "TAX": ["Cross-border routes", "Intercompany funding", "Withholding tax", "Transfer pricing review"],
        "AUDIT": ["Audit trail", "Approvals", "Model lineage", "Control evidence", "Exceptions"],
    }[normalized]
    return RoleWorkspaceOut(
        role=normalized,
        open_items=len(queue),
        critical_items=sum(1 for x in queue if x.severity == "CRITICAL"),
        high_items=sum(1 for x in queue if x.severity == "HIGH"),
        queue=queue,
        recommended_panels=panels,
        warnings=["Workspace prioritization is advisory; case ownership and closure require authenticated human actions."],
    )


def production_readiness(db: Session) -> ProductionReadinessOut:
    rows = db.scalars(select(DeploymentReadinessControl).order_by(DeploymentReadinessControl.category, DeploymentReadinessControl.control_code)).all()
    out = [ProductionReadinessRow(
        control_code=r.control_code,
        category=r.category,
        status=r.status,
        required=r.required,
        owner=r.owner,
        evidence=r.evidence,
    ) for r in rows]
    required = [r for r in rows if r.required]
    passed = sum(1 for r in required if r.status == "PASS")
    blocked = sum(1 for r in required if r.status != "PASS")
    pct = Decimal(passed) / Decimal(len(required)) if required else ZERO
    overall = "GO" if blocked == 0 and required else "NO_GO"
    return ProductionReadinessOut(
        release="MVP-22",
        overall_status=overall,
        readiness_pct=_q(pct, "0.0001"),
        required_controls=len(required),
        passed_controls=passed,
        blocked_controls=blocked,
        rows=out,
        deployment_authority="HUMAN_RELEASE_BOARD_ONLY",
        warnings=[
            "MVP-22 includes predictive and strategic intelligence on top of the MVP-20 production-readiness architecture; it is not a certification that a real MNC environment is production-ready.",
            "Live bank/ERP credentials, penetration testing, provider certification, tax/legal sign-off, load tests and DR exercises remain environment-specific gates.",
        ],
    )
