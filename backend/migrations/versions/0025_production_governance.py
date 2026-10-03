"""Phases 2-4: release evidence, parallel run, sign-offs and release ledger."""
from alembic import op
from app.models.production import (
    ProductionRelease, ProductionEvidence, ProductionSignoff,
    ProductionObservation, ProductionEvent,
)

revision = "0025_production_governance"
down_revision = "0024_parallel_validation"
branch_labels = None
depends_on = None


def upgrade():
    for model in (ProductionRelease, ProductionEvidence, ProductionSignoff,
                  ProductionObservation, ProductionEvent):
        model.__table__.create(op.get_bind(), checkfirst=True)


def downgrade():
    for model in (ProductionEvent, ProductionObservation, ProductionSignoff,
                  ProductionEvidence, ProductionRelease):
        model.__table__.drop(op.get_bind(), checkfirst=True)
