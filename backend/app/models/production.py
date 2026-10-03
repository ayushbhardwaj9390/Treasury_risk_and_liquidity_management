"""Release-scoped production evidence. No seeded approvals or certifications."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, Index, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class ProductionRelease(Base):
    __tablename__ = "production_releases"
    __table_args__ = (Index("uq_one_live_release", "state", unique=True,
                           sqlite_where=text("state = 'LIVE'"), postgresql_where=text("state = 'LIVE'")),)
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    artifact_sha256: Mapped[str] = mapped_column(String(64))
    previous_artifact_sha256: Mapped[str] = mapped_column(String(64))
    created_by: Mapped[str] = mapped_column(String(80))
    state: Mapped[str] = mapped_column(String(30), default="DRAFT")
    created_at: Mapped[datetime] = mapped_column(DateTime)


class ProductionEvidence(Base):
    __tablename__ = "production_evidence"
    id: Mapped[int] = mapped_column(primary_key=True)
    release_id: Mapped[int] = mapped_column(ForeignKey("production_releases.id"), index=True)
    gate: Mapped[str] = mapped_column(String(60))
    kind: Mapped[str] = mapped_column(String(20))
    result: Mapped[str] = mapped_column(String(20))
    document_sha256: Mapped[str] = mapped_column(String(64))
    reference: Mapped[str] = mapped_column(Text)
    scope: Mapped[str] = mapped_column(String(160))
    recorded_by: Mapped[str] = mapped_column(String(80))
    recorded_at: Mapped[datetime] = mapped_column(DateTime)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    details_json: Mapped[str] = mapped_column(Text, default="{}")


class ProductionSignoff(Base):
    __tablename__ = "production_signoffs"
    __table_args__ = (UniqueConstraint("release_id", "role", "evidence_digest"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    release_id: Mapped[int] = mapped_column(ForeignKey("production_releases.id"), index=True)
    role: Mapped[str] = mapped_column(String(40))
    actor: Mapped[str] = mapped_column(String(80))
    evidence_digest: Mapped[str] = mapped_column(String(64))
    decision: Mapped[str] = mapped_column(String(20))
    reason: Mapped[str] = mapped_column(Text)
    signed_at: Mapped[datetime] = mapped_column(DateTime)


class ProductionObservation(Base):
    __tablename__ = "production_observations"
    __table_args__ = (UniqueConstraint("release_id", "day", "metric", "scope"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    release_id: Mapped[int] = mapped_column(ForeignKey("production_releases.id"), index=True)
    day: Mapped[str] = mapped_column(String(10))
    metric: Mapped[str] = mapped_column(String(40))
    scope: Mapped[str] = mapped_column(String(160))
    kind: Mapped[str] = mapped_column(String(20))
    incumbent: Mapped[str] = mapped_column(String(100))
    platform: Mapped[str] = mapped_column(String(100))
    passed: Mapped[bool] = mapped_column()
    material: Mapped[bool] = mapped_column()
    document_sha256: Mapped[str] = mapped_column(String(64))
    actor: Mapped[str] = mapped_column(String(80))


class ProductionEvent(Base):
    __tablename__ = "production_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    release_id: Mapped[int] = mapped_column(ForeignKey("production_releases.id"), index=True)
    action: Mapped[str] = mapped_column(String(40))
    actor: Mapped[str] = mapped_column(String(80))
    reason: Mapped[str] = mapped_column(Text)
    recorded_at: Mapped[datetime] = mapped_column(DateTime)
