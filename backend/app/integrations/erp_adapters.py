from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Awaitable, Callable

import httpx


TokenProvider = Callable[[], Awaitable[str]]


@dataclass(frozen=True)
class ERPFlowRecord:
    external_reference: str
    legal_entity_code: str
    flow_type: str
    counterparty: str
    currency: str
    amount: Decimal
    due_date: date
    probability: Decimal
    status: str
    source_timestamp: datetime | None = None


def _parse_date(value: Any) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    text = str(value or "")
    if text.startswith("/Date("):
        millis = int(text.split("(", 1)[1].split(")", 1)[0].split("+", 1)[0])
        return datetime.fromtimestamp(millis / 1000, tz=timezone.utc).date()
    return date.fromisoformat(text[:10])


class SAPS4HanaConnector:
    """Read-only SAP S/4HANA finance adapter.

    Defaults to SAP's Journal Entry Item - Read OData service. Field mapping is explicit
    because SAP extensions and release-specific field sets differ across landscapes.
    """

    DEFAULT_PATH = "/sap/opu/odata/sap/API_JOURNALENTRYITEMBASIC_SRV/A_JournalEntryItemBasic/"

    def __init__(self, base_url: str, token_provider: TokenProvider, timeout_seconds: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.token_provider = token_provider
        self.timeout_seconds = timeout_seconds

    async def fetch_open_items(self, path: str | None = None, params: dict[str, str] | None = None) -> list[dict[str, Any]]:
        token = await self.token_provider()
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.get(
                self.base_url + (path or self.DEFAULT_PATH),
                params=params or {},
                headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            )
            response.raise_for_status()
            body = response.json()
        if isinstance(body.get("value"), list):
            return body["value"]
        if isinstance(body.get("d", {}).get("results"), list):
            return body["d"]["results"]
        raise ValueError("Unsupported SAP OData response shape")

    @staticmethod
    def normalize_open_items(items: list[dict[str, Any]], flow_type: str) -> list[ERPFlowRecord]:
        out: list[ERPFlowRecord] = []
        wanted = flow_type.upper()
        for row in items:
            company = str(row.get("CompanyCode") or row.get("CompanyCodeName") or "").strip()
            currency = str(row.get("TransactionCurrency") or row.get("CompanyCodeCurrency") or "").strip().upper()
            amount_raw = row.get("AmountInTransactionCurrency") or row.get("AmountInCompanyCodeCurrency")
            due = row.get("NetDueDate") or row.get("DueCalculationBaseDate") or row.get("PostingDate")
            reference = str(row.get("AccountingDocument") or row.get("ReferenceDocument") or row.get("OriginalReferenceDocument") or "").strip()
            counterparty = str(row.get("Customer") or row.get("Supplier") or row.get("GLAccount") or "UNKNOWN").strip()
            if not company or not currency or amount_raw is None or not due or not reference:
                continue
            amount = abs(Decimal(str(amount_raw)))
            out.append(ERPFlowRecord(reference, company, wanted, counterparty, currency, amount, _parse_date(due), Decimal("1"), "OPEN"))
        return out


class OracleFusionFinancialsConnector:
    """Read-only Oracle Fusion Cloud Financials adapter for AR/AP invoices."""

    RECEIVABLES_PATH = "/fscmRestApi/resources/11.13.18.05/receivablesInvoices"
    PAYABLES_PATH = "/fscmRestApi/resources/11.13.18.05/invoices"

    def __init__(self, base_url: str, token_provider: TokenProvider, timeout_seconds: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.token_provider = token_provider
        self.timeout_seconds = timeout_seconds

    async def _fetch(self, path: str, params: dict[str, str] | None = None) -> list[dict[str, Any]]:
        token = await self.token_provider()
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.get(
                self.base_url + path,
                params=params or {},
                headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            )
            response.raise_for_status()
            body = response.json()
        items = body.get("items")
        if not isinstance(items, list):
            raise ValueError("Unsupported Oracle Fusion REST response shape")
        return items

    async def fetch_receivables(self, params: dict[str, str] | None = None) -> list[dict[str, Any]]:
        return await self._fetch(self.RECEIVABLES_PATH, params)

    async def fetch_payables(self, params: dict[str, str] | None = None) -> list[dict[str, Any]]:
        return await self._fetch(self.PAYABLES_PATH, params)

    @staticmethod
    def normalize_invoices(items: list[dict[str, Any]], flow_type: str) -> list[ERPFlowRecord]:
        out: list[ERPFlowRecord] = []
        wanted = flow_type.upper()
        for row in items:
            reference = str(row.get("TransactionNumber") or row.get("InvoiceNumber") or row.get("CustomerTransactionId") or row.get("InvoiceId") or "").strip()
            company = str(row.get("BusinessUnit") or row.get("BusinessUnitName") or row.get("LedgerName") or "").strip()
            currency = str(row.get("InvoiceCurrencyCode") or row.get("Currency") or row.get("EnteredCurrency") or "").strip().upper()
            amount_raw = row.get("OriginalAmount") or row.get("InvoiceAmount") or row.get("Amount")
            due = row.get("DueDate") or row.get("TermsDate") or row.get("TransactionDate") or row.get("InvoiceDate")
            counterparty = str(row.get("BillToCustomerName") or row.get("Supplier") or row.get("SupplierName") or "UNKNOWN").strip()
            if not reference or not company or not currency or amount_raw is None or not due:
                continue
            out.append(ERPFlowRecord(reference, company, wanted, counterparty, currency, abs(Decimal(str(amount_raw))), _parse_date(due), Decimal("1"), "OPEN"))
        return out
