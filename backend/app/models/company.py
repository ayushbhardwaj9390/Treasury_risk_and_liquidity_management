"""Company setup metadata for a dedicated customer deployment."""
from datetime import UTC, datetime
from sqlalchemy import CheckConstraint, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column
from app.core.db import Base


class CompanyProfile(Base):
    __tablename__ = "company_profiles"
    __table_args__ = (CheckConstraint("id = 1", name="single_company_deployment"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    company_name: Mapped[str] = mapped_column(String(160))
    industry: Mapped[str] = mapped_column(String(40))
    country_code: Mapped[str] = mapped_column(String(2))
    version: Mapped[int] = mapped_column(default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None))


class CompanyEntityRegistration(Base):
    """Pending metadata; deliberately separate from engine-authoritative entities."""
    __tablename__ = "company_entity_registrations"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    name_key: Mapped[str] = mapped_column(String(480), unique=True)
    country_code: Mapped[str] = mapped_column(String(2))
    functional_currency: Mapped[str] = mapped_column(String(3))
    created_by: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None))
