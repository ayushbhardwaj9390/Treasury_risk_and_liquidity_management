from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import BankAccount, CreditFacility, LegalEntity
from app.schemas.treasury import GlobalLiquidityOut, LiquidityComponent
from app.services.fx import FXConversionError, convert


ZERO = Decimal("0")


def _to_functional(db: Session, amount: Decimal, currency: str, functional_currency: str, warnings: list[str], label: str) -> Decimal:
    try:
        return convert(db, Decimal(amount), currency, functional_currency)
    except FXConversionError as exc:
        warnings.append(f"{label}: {exc}")
        return ZERO


def _entity_liquidity(db: Session, entity: LegalEntity) -> tuple[LiquidityComponent, list[str]]:
    warnings: list[str] = []
    accounts = db.scalars(select(BankAccount).where(BankAccount.entity_id == entity.id)).all()
    facilities = db.scalars(select(CreditFacility).where(CreditFacility.entity_id == entity.id)).all()

    # Every balance/facility is translated into the entity functional currency before aggregation.
    # This prevents a multi-currency bank account from being incorrectly treated as local currency.
    gross = restricted = committed = ZERO
    for account in accounts:
        gross += _to_functional(db, account.book_balance, account.currency, entity.functional_currency, warnings, f"{entity.name}/{account.bank_name}")
        restricted += _to_functional(db, account.restricted_balance, account.currency, entity.functional_currency, warnings, f"{entity.name}/{account.bank_name}")
        committed += _to_functional(db, account.committed_outflows, account.currency, entity.functional_currency, warnings, f"{entity.name}/{account.bank_name}")

    deployable = gross - restricted - committed
    undrawn = ZERO
    for facility in facilities:
        if not facility.committed:
            continue
        local_undrawn = max(Decimal(facility.limit_amount) - Decimal(facility.drawn_amount), ZERO)
        undrawn += _to_functional(db, local_undrawn, facility.currency, entity.functional_currency, warnings, f"{entity.name}/{facility.lender}")

    try:
        deployable_reporting = convert(db, deployable, entity.functional_currency, settings.group_reporting_currency)
        minimum_reporting = convert(db, Decimal(entity.minimum_cash), entity.functional_currency, settings.group_reporting_currency)
        undrawn_reporting = convert(db, undrawn, entity.functional_currency, settings.group_reporting_currency)
    except FXConversionError as exc:
        warnings.append(str(exc))
        deployable_reporting = minimum_reporting = undrawn_reporting = ZERO

    headroom = deployable_reporting + undrawn_reporting - minimum_reporting

    if not accounts:
        warnings.append(f"{entity.name}: no bank accounts loaded")
    if deployable < 0:
        warnings.append(f"{entity.name}: committed/restricted cash exceeds book cash")
    if headroom < 0:
        warnings.append(f"{entity.name}: negative liquidity headroom")

    return LiquidityComponent(
        entity_id=entity.id,
        entity_name=entity.name,
        local_currency=entity.functional_currency,
        reporting_currency=settings.group_reporting_currency,
        gross_cash_local=gross,
        restricted_cash_local=restricted,
        committed_outflows_local=committed,
        deployable_cash_local=deployable,
        minimum_cash_local=Decimal(entity.minimum_cash),
        undrawn_credit_local=undrawn,
        deployable_cash_reporting=deployable_reporting,
        minimum_cash_reporting=minimum_reporting,
        undrawn_credit_reporting=undrawn_reporting,
        liquidity_headroom_reporting=headroom,
    ), warnings


def calculate_global_liquidity(db: Session) -> GlobalLiquidityOut:
    entities = db.scalars(select(LegalEntity).where(LegalEntity.active.is_(True)).order_by(LegalEntity.name)).all()
    components: list[LiquidityComponent] = []
    warnings: list[str] = []

    gross = restricted = committed = deployable = minimum = undrawn = headroom = ZERO

    for entity in entities:
        component, entity_warnings = _entity_liquidity(db, entity)
        components.append(component)
        warnings.extend(entity_warnings)

        try:
            gross += convert(db, component.gross_cash_local, entity.functional_currency, settings.group_reporting_currency)
            restricted += convert(db, component.restricted_cash_local, entity.functional_currency, settings.group_reporting_currency)
            committed += convert(db, component.committed_outflows_local, entity.functional_currency, settings.group_reporting_currency)
        except FXConversionError as exc:
            warnings.append(f"{entity.name}: {exc}")
        deployable += component.deployable_cash_reporting
        minimum += component.minimum_cash_reporting
        undrawn += component.undrawn_credit_reporting
        headroom += component.liquidity_headroom_reporting

    return GlobalLiquidityOut(
        reporting_currency=settings.group_reporting_currency,
        gross_cash=gross,
        restricted_cash=restricted,
        committed_outflows=committed,
        deployable_cash=deployable,
        minimum_cash=minimum,
        undrawn_credit=undrawn,
        liquidity_headroom=headroom,
        data_as_of=datetime.now(timezone.utc),
        entities=components,
        warnings=warnings,
    )
