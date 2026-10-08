"""Schedules describe requested collection; they do not grant source authority."""
from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column
from app.core.db import Base


class ScheduledUpdate(Base):
    __tablename__ = "scheduled_updates"
    id: Mapped[int] = mapped_column(primary_key=True)
    connector_id: Mapped[int] = mapped_column(ForeignKey("source_connectors.id"), unique=True)
    interval_minutes: Mapped[int] = mapped_column(default=60)
    stale_after_minutes: Mapped[int] = mapped_column(default=120)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    version: Mapped[int] = mapped_column(default=1)
    next_due_at: Mapped[datetime] = mapped_column(DateTime)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_attempt_status: Mapped[str] = mapped_column(String(24), default="NOT_ATTEMPTED")
    last_attempt_reason: Mapped[str] = mapped_column(String(240), default="No worker attempt recorded.")
