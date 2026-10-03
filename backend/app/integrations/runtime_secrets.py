from __future__ import annotations

import os

from app.core.config import settings


async def runtime_secret(secret_name: str | None) -> str:
    """Resolve a connector credential without persisting it in the treasury database.

    ENV resolution is allowed for local/UAT reference deployments. Production deliberately
    fails closed until the deployment injects a managed SecretProvider implementation.
    """
    if not secret_name:
        raise RuntimeError("Connector credential secret name is not configured")
    provider = settings.secret_provider.upper()
    if settings.environment.lower() == "production" and provider in {"", "UNCONFIGURED", "ENV"}:
        raise RuntimeError("Production connector credentials require a managed secret provider; ENV/UNCONFIGURED is refused")
    value = os.getenv(secret_name)
    if not value:
        raise RuntimeError(f"Secret {secret_name} is not available from the configured runtime provider")
    return value
