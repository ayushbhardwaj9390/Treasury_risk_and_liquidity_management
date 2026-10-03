"""Negative identity tests and production startup checks, without external IdP."""
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.core import security
from app.core.config import settings
from app.main import app


@pytest.fixture
def identity(monkeypatch):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    monkeypatch.setattr(settings, "oidc_issuer", "https://idp.example")
    monkeypatch.setattr(settings, "oidc_audience", "treasury")
    monkeypatch.setattr(settings, "oidc_jwks_url", "https://idp.example/keys")
    client = type("Keys", (), {"get_signing_key_from_jwt": lambda self, token: type("Key", (), {"key": key.public_key()})()})()
    monkeypatch.setattr(security, "_jwks_client", lambda url: client)
    return key


@pytest.mark.parametrize("change", ["expiry", "audience", "issuer", "signature", "subject"])
def test_signed_tokens_reject_invalid_claims(identity, change):
    claims = {"iss": "https://idp.example", "aud": "treasury", "sub": "risk",
              "iat": datetime.now(UTC), "exp": datetime.now(UTC) + timedelta(minutes=5)}
    if change == "expiry":
        claims["exp"] = datetime.now(UTC) - timedelta(minutes=5)
    if change == "audience":
        claims["aud"] = "other"
    if change == "issuer":
        claims["iss"] = "https://other.example"
    if change == "subject":
        del claims["sub"]
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048) if change == "signature" else identity
    token = jwt.encode(claims, key, algorithm="RS256")
    with pytest.raises(HTTPException) as error:
        security._verified_oidc_identity("Bearer " + token)
    assert error.value.status_code == 401


def test_valid_signed_identity(identity):
    token = jwt.encode({"iss": "https://idp.example", "aud": "treasury", "sub": "risk",
                       "iat": datetime.now(UTC), "exp": datetime.now(UTC) + timedelta(minutes=5)}, identity, algorithm="RS256")
    assert security._verified_oidc_identity("Bearer " + token) == "risk"


def test_production_rejects_demo_startup(monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "auth_mode", "demo_header")
    with pytest.raises(RuntimeError, match="OIDC"):
        with TestClient(app):
            pass
