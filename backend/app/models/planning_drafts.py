"""Persisted planning inputs; deliberately outside authoritative engine tables."""
from datetime import UTC, datetime
from sqlalchemy import CheckConstraint, DateTime, JSON, String
from sqlalchemy.orm import Mapped, mapped_column
from app.core.db import Base


class PlanningDraft(Base):
    __tablename__ = "company_planning_drafts"
    __table_args__ = (CheckConstraint("id = 1", name="single_company_planning_draft"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    payload: Mapped[dict] = mapped_column(JSON)
    version: Mapped[int] = mapped_column(default=1)
    updated_by: Mapped[str] = mapped_column(String(80))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None))
