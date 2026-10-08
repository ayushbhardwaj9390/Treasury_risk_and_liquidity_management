"""Request controls must protect rejected responses as well as downstream responses."""
import asyncio
from contextlib import nullcontext
from uuid import UUID

import pytest
from fastapi import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse

from app import main
from app.core import security
from app.core.config import settings
from app.services import enterprise_controls


def request(method="POST", path="/api/v1/transactions/propose", body=b"{}"):
    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}
    return Request({"type": "http", "method": method, "path": path,
                    "headers": [], "scheme": "https", "server": ("testserver", 443),
                    "query_string": b""}, receive)


@pytest.fixture
def production(monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "security_headers_enabled", True)
    monkeypatch.setattr(settings, "production_write_idempotency_required", True)
    monkeypatch.setattr(settings, "max_request_bytes", 10)
    monkeypatch.setattr(settings, "metrics_enabled", False)
    monkeypatch.setattr(security, "treasury_identity", lambda *args: "test-user")
    monkeypatch.setattr(main, "SessionLocal", lambda: nullcontext(object()))
    monkeypatch.setattr(enterprise_controls, "_user", lambda *args: None)


def assert_headers(response):
    UUID(response.headers["X-Request-ID"])
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert response.headers["Content-Security-Policy"] == "default-src 'self'; frame-ancestors 'none'"
    assert response.headers["Strict-Transport-Security"] == "max-age=31536000; includeSubDomains"


@pytest.mark.parametrize("failure,status", [("identity", 401), ("account", 403),
                                            ("size", 413), ("idempotency", 428)])
def test_rejected_request_headers(production, monkeypatch, failure, status):
    if failure in {"identity", "account"}:
        def deny(*args):
            if failure == "identity":
                raise HTTPException(status_code=401, detail="Invalid token")
            raise PermissionError("Account inactive")
        monkeypatch.setattr(security, "treasury_identity", deny)
    incoming = request(body=b"x" * 11 if failure == "size" else b"{}")
    async def downstream(_):
        pytest.fail("Rejected requests must not reach the endpoint")
    response = asyncio.run(main.enterprise_request_controls(incoming, downstream))
    assert response.status_code == status
    assert_headers(response)


def test_downstream_response_preserves_body_and_status(production):
    async def downstream(_):
        return JSONResponse({"detail": "Endpoint denied"}, status_code=409)
    response = asyncio.run(main.enterprise_request_controls(request("GET"), downstream))
    assert response.status_code == 409
    assert response.body == b'{"detail":"Endpoint denied"}'
    assert_headers(response)


def test_disabled_security_headers_still_assign_request_id(production, monkeypatch):
    monkeypatch.setattr(settings, "security_headers_enabled", False)
    async def downstream(_):
        pytest.fail("Missing idempotency key must remain rejected")
    response = asyncio.run(main.enterprise_request_controls(request(), downstream))
    assert response.status_code == 428
    UUID(response.headers["X-Request-ID"])
    assert "Strict-Transport-Security" not in response.headers
    assert "Content-Security-Policy" not in response.headers
