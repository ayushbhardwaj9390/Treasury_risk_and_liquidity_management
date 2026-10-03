from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, AwareDatetime

SHA256 = r"^[a-f0-9]{64}$"


class StrictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ReleaseCreate(StrictRequest):
    name: str = Field(min_length=1, max_length=100)
    artifact_sha256: str = Field(pattern=SHA256)
    previous_artifact_sha256: str = Field(pattern=SHA256)


class EvidenceCreate(StrictRequest):
    gate: str = Field(max_length=60)
    kind: Literal["REAL", "SYNTHETIC"]
    result: Literal["PASS", "FAIL"]
    document_sha256: str = Field(pattern=SHA256)
    reference: str = Field(min_length=1, max_length=2000)
    scope: str = Field(min_length=1, max_length=160)
    expires_at: AwareDatetime
    details: dict = Field(default_factory=dict)


class SignoffCreate(StrictRequest):
    evidence_digest: str = Field(pattern=SHA256)
    decision: Literal["APPROVE", "REJECT"]
    reason: str = Field(min_length=1, max_length=2000)


class ObservationCreate(StrictRequest):
    day: date
    metric: Literal["CASH", "FORECAST", "FX", "LIQUIDITY", "PAYMENTS", "RISK"]
    scope: str = Field(min_length=1, max_length=160)
    kind: Literal["REAL", "SYNTHETIC"]
    incumbent: Decimal = Field(allow_inf_nan=False, max_digits=28, decimal_places=8)
    platform: Decimal = Field(allow_inf_nan=False, max_digits=28, decimal_places=8)
    document_sha256: str = Field(pattern=SHA256)


class TransitionCreate(StrictRequest):
    action: Literal["START_PARALLEL", "GO_LIVE", "ROLLBACK", "HALT"]
    reason: str = Field(min_length=1, max_length=2000)


class BenchmarkCreate(StrictRequest):
    actual: list[Decimal] = Field(min_length=2, max_length=10000)
    predicted: list[Decimal] = Field(min_length=2, max_length=10000)
    challenger: list[Decimal] = Field(min_length=2, max_length=10000)
