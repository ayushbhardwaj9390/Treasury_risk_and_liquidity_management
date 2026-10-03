from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Iterable
import hashlib

from defusedxml import ElementTree as ET


@dataclass(frozen=True)
class ParsedBankBalance:
    external_account_id: str
    currency: str
    book_balance: Decimal
    available_balance: Decimal | None
    as_of: datetime
    source_record_id: str


@dataclass(frozen=True)
class ParsedBankTransaction:
    external_account_id: str
    source_record_id: str
    booking_date: datetime
    value_date: datetime | None
    currency: str
    amount: Decimal
    credit_debit: str
    counterparty: str
    reference: str
    status: str


@dataclass(frozen=True)
class ISO20022ParseResult:
    message_type: str
    balances: list[ParsedBankBalance]
    transactions: list[ParsedBankTransaction]
    warnings: list[str]


def _local(tag: str) -> str:
    return tag.split("}", 1)[-1]


def _children(node, name: str) -> Iterable:
    for child in node.iter():
        if _local(child.tag) == name:
            yield child


def _first_text(node, *path_names: str) -> str | None:
    current = node
    for name in path_names:
        found = None
        for child in list(current):
            if _local(child.tag) == name:
                found = child
                break
        if found is None:
            return None
        current = found
    text = (current.text or "").strip()
    return text or None


def _parse_iso_dt(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc).replace(tzinfo=None)
    value = value.strip()
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        dt = datetime.fromisoformat(value[:10])
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def _balance_date(balance_node) -> datetime:
    dt = _first_text(balance_node, "Dt", "DtTm") or _first_text(balance_node, "Dt", "Dt")
    return _parse_iso_dt(dt)


def parse_camt_cash_report(xml_payload: str) -> ISO20022ParseResult:
    """Parse ISO 20022 camt.052/camt.053 cash balances into a canonical balance list.

    The parser is deliberately conservative: if an account or closing balance cannot be
    mapped unambiguously, the record is omitted and a warning is emitted instead of
    guessing. camt.054 is detected but is not treated as a balance statement.
    """
    root = ET.fromstring(xml_payload)
    root_names = {_local(x.tag) for x in root.iter()}
    if "BkToCstmrStmt" in root_names:
        message_type = "camt.053"
        container_name = "Stmt"
    elif "BkToCstmrAcctRpt" in root_names:
        message_type = "camt.052"
        container_name = "Rpt"
    elif "BkToCstmrDbtCdtNtfctn" in root_names:
        message_type = "camt.054"
        container_name = "Ntfctn"
    else:
        raise ValueError("Unsupported ISO 20022 cash-management message; expected camt.052, camt.053 or camt.054")

    balances: list[ParsedBankBalance] = []
    transactions: list[ParsedBankTransaction] = []
    warnings: list[str] = []
    for statement in _children(root, container_name):
        iban = _first_text(statement, "Acct", "Id", "IBAN")
        other = _first_text(statement, "Acct", "Id", "Othr", "Id")
        account_id = iban or other
        if not account_id:
            warnings.append("Skipped statement/report with no account identifier")
            continue

        selected_book: tuple[Decimal, str, datetime] | None = None
        selected_available: tuple[Decimal, datetime] | None = None
        bal_no = 0
        for bal in list(statement):
            if _local(bal.tag) != "Bal":
                continue
            bal_no += 1
            code = _first_text(bal, "Tp", "CdOrPrtry", "Cd") or _first_text(bal, "Tp", "CdOrPrtry", "Prtry") or "UNKNOWN"
            amount_node = next((x for x in list(bal) if _local(x.tag) == "Amt"), None)
            if amount_node is None or not (amount_node.text or "").strip():
                continue
            currency = (amount_node.attrib.get("Ccy") or "").upper()
            if not currency:
                warnings.append(f"{account_id}: skipped balance without currency")
                continue
            amount = Decimal((amount_node.text or "0").strip())
            indicator = _first_text(bal, "CdtDbtInd")
            if indicator == "DBIT":
                amount = -amount
            as_of = _balance_date(bal)
            if code in {"CLBD", "ITBD"}:
                if selected_book is None or as_of >= selected_book[2]:
                    selected_book = (amount, currency, as_of)
            elif code in {"CLAV", "ITAV", "XPCD"}:
                if selected_available is None or as_of >= selected_available[1]:
                    selected_available = (amount, as_of)

        if selected_book is None:
            if message_type != "camt.054":
                warnings.append(f"{account_id}: no CLBD/ITBD book balance found")
        else:
            book, currency, as_of = selected_book
            available = selected_available[0] if selected_available else None
            source_record_id = f"{message_type}:{account_id}:{as_of.isoformat()}"
            balances.append(ParsedBankBalance(account_id, currency, book, available, as_of, source_record_id))

        for entry in list(statement):
            if _local(entry.tag) != "Ntry":
                continue
            amount_node = next((x for x in list(entry) if _local(x.tag) == "Amt"), None)
            if amount_node is None or not (amount_node.text or "").strip():
                continue
            currency = (amount_node.attrib.get("Ccy") or "").upper()
            if not currency:
                warnings.append(f"{account_id}: skipped entry without currency")
                continue
            amount = abs(Decimal((amount_node.text or "0").strip()))
            indicator = (_first_text(entry, "CdtDbtInd") or "CRDT").upper()
            signed = -amount if indicator == "DBIT" else amount
            book_dt = _parse_iso_dt(_first_text(entry, "BookgDt", "DtTm") or _first_text(entry, "BookgDt", "Dt"))
            val_raw = _first_text(entry, "ValDt", "DtTm") or _first_text(entry, "ValDt", "Dt")
            val_dt = _parse_iso_dt(val_raw) if val_raw else None
            reference = (_first_text(entry, "NtryRef") or _first_text(entry, "AcctSvcrRef") or "").strip()
            counterparty = ""
            for node in entry.iter():
                if _local(node.tag) in {"Nm", "Name"} and (node.text or "").strip():
                    counterparty = (node.text or "").strip()
                    break
            if not reference:
                material = f"{account_id}|{book_dt.isoformat()}|{currency}|{signed}|{counterparty}"
                reference = "AUTO-" + hashlib.sha256(material.encode()).hexdigest()[:20]
            source_record_id = f"{message_type}:{account_id}:{reference}"
            status = (_first_text(entry, "Sts", "Cd") or _first_text(entry, "Sts") or "BOOK").upper()
            transactions.append(ParsedBankTransaction(
                external_account_id=account_id, source_record_id=source_record_id, booking_date=book_dt,
                value_date=val_dt, currency=currency, amount=signed, credit_debit=indicator,
                counterparty=counterparty, reference=reference, status=status,
            ))

    return ISO20022ParseResult(message_type, balances, transactions, warnings)
