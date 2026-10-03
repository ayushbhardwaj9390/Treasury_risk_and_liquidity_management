from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True)
class CanonicalConnectorEnvelope:
    event_id: str
    connector_code: str
    contract_version: str
    occurred_at: datetime
    received_at: datetime
    entity_code: str | None
    payload_type: str
    payload_hash: str
    idempotency_key: str


class WorkloadIdentityProvider(Protocol):
    async def token(self, audience: str) -> str: ...


class SecretProvider(Protocol):
    async def get_secret(self, name: str) -> str: ...


class HSMOrKmsSigner(Protocol):
    async def sign(self, payload: bytes, key_id: str) -> bytes: ...
    async def verify(self, payload: bytes, signature: bytes, key_id: str) -> bool: ...


class SIEMSink(Protocol):
    async def emit_security_event(self, event_type: str, severity: str, details: dict) -> None: ...


class AuditEvidenceSink(Protocol):
    async def write_evidence(self, control_code: str, payload: dict) -> str: ...


def validate_canonical_envelope(envelope: CanonicalConnectorEnvelope, supported_version: str = "1.0") -> list[str]:
    errors: list[str] = []
    if envelope.contract_version != supported_version:
        errors.append(f"Unsupported contract version {envelope.contract_version}; expected {supported_version}")
    if not envelope.event_id.strip():
        errors.append("event_id is required")
    if not envelope.connector_code.strip():
        errors.append("connector_code is required")
    if not envelope.payload_hash.strip():
        errors.append("payload_hash is required")
    if not envelope.idempotency_key.strip():
        errors.append("idempotency_key is required")
    if envelope.received_at < envelope.occurred_at:
        errors.append("received_at cannot precede occurred_at")
    return errors
