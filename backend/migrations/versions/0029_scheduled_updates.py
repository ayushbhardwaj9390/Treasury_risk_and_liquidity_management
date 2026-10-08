"""Persist requested update schedules, never source authority."""
from alembic import op
from app.models.scheduled_updates import ScheduledUpdate
revision = "0029_scheduled_updates"
down_revision = "0028_company_preferences"
branch_labels = None
depends_on = None


def upgrade():
    ScheduledUpdate.__table__.create(op.get_bind(), checkfirst=True)


def downgrade():
    ScheduledUpdate.__table__.drop(op.get_bind(), checkfirst=True)
