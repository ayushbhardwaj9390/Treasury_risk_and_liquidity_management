from collections import defaultdict
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import BankAccount, CashFlow, DerivativePosition
from app.schemas.treasury import FXExposureRow


ZERO = Decimal("0")


def calculate_fx_exposures(db: Session) -> list[FXExposureRow]:
    data = defaultdict(lambda: {"cash": ZERO, "receivables": ZERO, "payables": ZERO, "derivative": ZERO})

    for account in db.scalars(select(BankAccount)).all():
        data[account.currency]["cash"] += Decimal(account.book_balance) - Decimal(account.restricted_balance)

    for flow in db.scalars(select(CashFlow).where(CashFlow.status == "OPEN")).all():
        expected = Decimal(flow.amount) * Decimal(flow.probability)
        if flow.flow_type == "RECEIVABLE":
            data[flow.currency]["receivables"] += expected
        elif flow.flow_type == "PAYABLE":
            data[flow.currency]["payables"] += expected

    for trade in db.scalars(select(DerivativePosition).where(DerivativePosition.status == "OPEN")).all():
        if not trade.instrument_type.startswith("FX_") and trade.instrument_type != "CROSS_CURRENCY_SWAP":
            continue
        sign = Decimal("1") if trade.hedge_direction == "BUY" else Decimal("-1")
        data[trade.exposure_currency]["derivative"] += sign * Decimal(trade.notional)

    rows = []
    for currency, values in sorted(data.items()):
        residual = values["cash"] + values["receivables"] - values["payables"] + values["derivative"]
        rows.append(
            FXExposureRow(
                currency=currency,
                cash=values["cash"],
                receivables=values["receivables"],
                payables=values["payables"],
                derivative_hedge=values["derivative"],
                residual_exposure=residual,
            )
        )
    return rows
