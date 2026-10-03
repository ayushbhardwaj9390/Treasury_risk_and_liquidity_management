from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Awaitable, Callable

import httpx

TokenProvider = Callable[[], Awaitable[str]]


@dataclass(frozen=True)
class NormalizedMarketQuote:
    instrument: str
    asset_class: str
    mid: Decimal
    bid: Decimal | None
    ask: Decimal | None
    as_of: datetime
    source: str
    source_record_id: str


class GenericMarketDataHTTPConnector:
    """Provider-neutral read-only HTTP market-data adapter.

    A production deployment supplies provider-specific endpoint/query mapping while this
    class enforces authentication, timeout and canonical quote normalization boundaries.
    """

    def __init__(self, base_url: str, token_provider: TokenProvider, timeout_seconds: float = 10.0):
        self.base_url = base_url.rstrip("/")
        self.token_provider = token_provider
        self.timeout_seconds = timeout_seconds

    async def fetch_json(self, path: str, params: dict[str, str] | None = None) -> dict[str, Any]:
        token = await self.token_provider()
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.get(
                self.base_url + path,
                params=params or {},
                headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            )
            response.raise_for_status()
            return response.json()
