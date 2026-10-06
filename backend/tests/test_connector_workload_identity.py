from datetime import UTC, datetime, timedelta

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException

from app.core import security
from app.core.config import settings


@pytest.fixture
def connector(monkeypatch):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "connector_oidc_issuer", "https://workloads.example")
    monkeypatch.setattr(settings, "connector_oidc_jwks_url", "https://workloads.example/keys")
    monkeypatch.setattr(settings, "workload_identity_audience", "treasury-ingest")
    monkeypatch.setattr(settings, "oidc_audience", "treasury-users")
    client = type("Keys", (), {"get_signing_key_from_jwt": lambda self, token: type("Key", (), {"key": key.public_key()})()})()
    monkeypatch.setattr(security, "_jwks_client", lambda url: client)
    return key


def token(key, **changes):
    claims = {"iss": "https://workloads.example", "aud": "treasury-ingest", "sub": "BANK_SERVICE",
              "iat": datetime.now(UTC), "exp": datetime.now(UTC) + timedelta(minutes=5),
              "preferred_username": "DIFFERENT_CONNECTOR"}
    claims.update(changes)
    return "Bearer " + jwt.encode(claims, key, algorithm="RS256")


def test_connector_subject_is_verified_and_header_cannot_override_it(connector):
    assert security.connector_identity("OTHER_BANK", token(connector)) == "BANK_SERVICE"


@pytest.mark.parametrize("change", ["user_audience", "issuer", "expiry", "signature", "empty_subject"])
def test_invalid_workload_token_is_rejected(connector, change):
    args = {}
    signing = connector
    if change == "user_audience": args["aud"] = "treasury-users"
    if change == "issuer": args["iss"] = "https://attacker.example"
    if change == "expiry": args["exp"] = datetime.now(UTC) - timedelta(minutes=5)
    if change == "empty_subject": args["sub"] = ""
    if change == "signature": signing = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    with pytest.raises(HTTPException) as error:
        security.connector_identity("BANK_SERVICE", token(signing, **args))
    assert error.value.status_code == 401


def test_production_header_alone_never_authenticates_connector(connector):
    with pytest.raises(HTTPException) as error:
        security.connector_identity("BANK_SERVICE", None)
    assert error.value.status_code == 401


def test_user_and_workload_audiences_must_differ(connector, monkeypatch):
    monkeypatch.setattr(settings, "workload_identity_audience", "treasury-users")
    with pytest.raises(HTTPException) as error:
        security.connector_identity(None, token(connector))
    assert error.value.status_code == 503
