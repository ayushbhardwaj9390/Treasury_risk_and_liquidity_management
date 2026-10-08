"""Dedicated company cash-planning inputs, not engine-authoritative records."""
from alembic import op
from app.models.planning_drafts import PlanningDraft

revision = "0027_planning_drafts"
down_revision = "0026_company_onboarding"
branch_labels = None
depends_on = None


def upgrade():
    PlanningDraft.__table__.create(op.get_bind(), checkfirst=True)


def downgrade():
    PlanningDraft.__table__.drop(op.get_bind(), checkfirst=True)
