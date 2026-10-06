"""Dedicated company setup; pending registrations never activate engine entities."""
from alembic import op
from app.models.company import CompanyProfile, CompanyEntityRegistration

revision = "0026_company_onboarding"
down_revision = "0025_production_governance"
branch_labels = None
depends_on = None


def upgrade():
    for model in (CompanyProfile, CompanyEntityRegistration):
        model.__table__.create(op.get_bind(), checkfirst=True)


def downgrade():
    for model in (CompanyEntityRegistration, CompanyProfile):
        model.__table__.drop(op.get_bind(), checkfirst=True)
