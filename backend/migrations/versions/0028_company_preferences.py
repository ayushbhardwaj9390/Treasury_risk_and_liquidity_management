"""Dedicated company draft preferences."""
from alembic import op
from app.models.company_preferences import CompanyPreferences

revision = "0028_company_preferences"
down_revision = "0027_planning_drafts"
branch_labels = None
depends_on = None


def upgrade():
    CompanyPreferences.__table__.create(op.get_bind(), checkfirst=True)


def downgrade():
    CompanyPreferences.__table__.drop(op.get_bind(), checkfirst=True)
