from __future__ import annotations
from functools import lru_cache

from fastapi import Header, HTTPException

from app.core.config import settings


@lru_cache(maxsize=4)
def _jwks_client(url: str):
    from jwt import PyJWKClient
    return PyJWKClient(url, timeout=10, lifespan=300)


def _verified_oidc_identity(authorization: str | None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Bearer token required")
    if not settings.oidc_issuer or not settings.oidc_audience or not settings.oidc_jwks_url:
        raise HTTPException(status_code=503, detail="OIDC verification is not fully configured")
    token = authorization.split(" ", 1)[1]
    try:
        import jwt
        from jwt import PyJWKClient
    except ImportError as exc:
        raise HTTPException(status_code=503, detail="PyJWT is required for OIDC verification in production") from exc
    try:
        signing_key = _jwks_client(settings.oidc_jwks_url).get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256", "ES256"],
            audience=settings.oidc_audience,
            issuer=settings.oidc_issuer,
            options={"require": ["exp", "iat", "sub"]},
        )
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid or unverifiable identity token") from exc
    username = claims.get(settings.oidc_username_claim) or claims.get("email") or claims.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="Identity token has no usable subject claim")
    return str(username)


def treasury_identity(
    x_treasury_user: str | None = Header(None, alias="X-Treasury-User"),
    authorization: str | None = Header(None, alias="Authorization"),
) -> str:
    """Enterprise identity boundary.

    Development uses a demo header. Production must use signed OIDC/JWT claims; the demo
    adapter is deliberately rejected in production.
    """
    mode = settings.auth_mode.lower()
    if mode == "oidc_jwt":
        return _verified_oidc_identity(authorization)
    if settings.environment.lower() == "production":
        raise HTTPException(
            status_code=503,
            detail="Demo header identity is disabled in production. Configure auth_mode=oidc_jwt.",
        )
    if not x_treasury_user:
        raise HTTPException(status_code=401, detail="X-Treasury-User is required in development demo mode")
    return x_treasury_user


def connector_identity(
    x_connector_name: str | None = Header(None, alias="X-Connector-Name"),
    authorization: str | None = Header(None, alias="Authorization"),
) -> str:
    """Connector identity boundary for bank/ERP/market adapters.

    Development uses X-Connector-Name. Production deliberately rejects that adapter until
    workload identity/mTLS/JWT verification is configured by the deployment platform.
    """
    if settings.environment.lower() == "production":
        raise HTTPException(
            status_code=503,
            detail="Demo connector identity is disabled in production. Configure verified workload identity/mTLS/JWT.",
        )
    if not x_connector_name:
        raise HTTPException(status_code=401, detail="X-Connector-Name is required in development demo mode")
    return x_connector_name
