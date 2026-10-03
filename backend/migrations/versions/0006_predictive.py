"""Bootstrap baseline for the current demo schema.

Revision ID: 0006_predictive

For an existing MVP-6 database, stamp this revision before applying 0007. For a fresh
installation this bootstrap creates the complete metadata schema, after which 0007 safely
recognizes that the institutional tables already exist.
"""
from alembic import op

from app.core.db import Base
import app.models  # noqa: F401

revision = "0006_predictive"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
