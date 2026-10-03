from __future__ import annotations

from typing import Any, Awaitable, Callable

import httpx

TokenProvider = Callable[[], Awaitable[str]]


class CanonicalBankHTTPConnector:
    """Read-only bank API adapter expecting a canonical integration-gateway contract.

    Direct bank APIs differ by provider. In production this connector normally points to a
    bank integration gateway that translates provider payloads into the platform's versioned
    canonical balance/transaction contract.
    """

    def __init__(self, base_url: str, token_provider: TokenProvider, timeout_seconds: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.token_provider = token_provider
        self.timeout_seconds = timeout_seconds

    async def _get(self, path: str, params: dict[str, str] | None = None) -> dict[str, Any]:
        token = await self.token_provider()
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.get(
                self.base_url + path,
                params=params or {},
                headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            )
            response.raise_for_status()
            body = response.json()
        if not isinstance(body, dict):
            raise ValueError("Bank integration gateway must return a JSON object")
        return body

    async def fetch_balances(self, watermark: str | None = None) -> dict[str, Any]:
        params = {"watermark": watermark} if watermark else None
        return await self._get("/treasury/v1/balances", params)

    async def fetch_transactions(self, watermark: str | None = None) -> dict[str, Any]:
        params = {"watermark": watermark} if watermark else None
        return await self._get("/treasury/v1/transactions", params)
