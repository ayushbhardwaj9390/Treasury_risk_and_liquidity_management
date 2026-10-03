from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Protocol


@dataclass(frozen=True)
class ConnectorHeartbeat:
    connector_name: str
    received_at: datetime
    status: str
    record_count: int = 0


@dataclass(frozen=True)
class BankBalanceRecord:
    external_account_id: str
    currency: str
    book_balance: Decimal
    available_balance: Decimal
    as_of: datetime


@dataclass(frozen=True)
class ERPExposureRecord:
    external_reference: str
    legal_entity_code: str
    exposure_type: str
    currency: str
    amount: Decimal
    due_at: datetime


@dataclass(frozen=True)
class MarketQuoteRecord:
    instrument: str
    asset_class: str
    bid: Decimal | None
    ask: Decimal | None
    mid: Decimal
    as_of: datetime
    source: str


class BankConnector(Protocol):
    async def heartbeat(self) -> ConnectorHeartbeat: ...
    async def fetch_balances(self) -> list[BankBalanceRecord]: ...


class ERPConnector(Protocol):
    async def heartbeat(self) -> ConnectorHeartbeat: ...
    async def fetch_exposures(self) -> list[ERPExposureRecord]: ...


class MarketDataConnector(Protocol):
    async def heartbeat(self) -> ConnectorHeartbeat: ...
    async def fetch_quotes(self, instruments: list[str]) -> list[MarketQuoteRecord]: ...


# These are interface contracts only. Production implementations must add authentication,
# idempotency, schema/version checks, retries, observability, and vendor-specific controls.


@dataclass(frozen=True)
class ExecutionInstruction:
    instruction_id: str
    idempotency_key: str
    instruction_type: str
    currency: str
    amount: Decimal
    value_date: datetime
    source_account: str | None = None
    target_account: str | None = None
    counterparty: str | None = None
    approved_by: tuple[str, ...] = ()


@dataclass(frozen=True)
class ExecutionAcknowledgement:
    instruction_id: str
    provider_reference: str
    status: str
    received_at: datetime
    rejection_reason: str | None = None


class ExecutionConnector(Protocol):
    async def heartbeat(self) -> ConnectorHeartbeat: ...
    async def submit(self, instruction: ExecutionInstruction) -> ExecutionAcknowledgement: ...
    async def status(self, provider_reference: str) -> ExecutionAcknowledgement: ...
