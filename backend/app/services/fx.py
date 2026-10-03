from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import FXRate


class FXConversionError(ValueError):
    pass


def latest_rate(db: Session, base: str, quote: str) -> Decimal:
    base = base.upper()
    quote = quote.upper()
    if base == quote:
        return Decimal("1")

    direct = db.scalar(
        select(FXRate)
        .where(FXRate.base_currency == base, FXRate.quote_currency == quote)
        .order_by(FXRate.as_of.desc())
        .limit(1)
    )
    if direct:
        return Decimal(direct.rate)

    inverse = db.scalar(
        select(FXRate)
        .where(FXRate.base_currency == quote, FXRate.quote_currency == base)
        .order_by(FXRate.as_of.desc())
        .limit(1)
    )
    if inverse and Decimal(inverse.rate) != 0:
        return Decimal("1") / Decimal(inverse.rate)

    # Triangulate via USD when possible.
    if base != "USD" and quote != "USD":
        return latest_rate(db, base, "USD") * latest_rate(db, "USD", quote)

    raise FXConversionError(f"Missing FX rate for {base}/{quote}")


def convert(db: Session, amount: Decimal, base: str, quote: str) -> Decimal:
    return Decimal(amount) * latest_rate(db, base, quote)
