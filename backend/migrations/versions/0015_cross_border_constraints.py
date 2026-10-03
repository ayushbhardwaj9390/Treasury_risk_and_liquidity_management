"""MVP-15 cross-border constraint graph.

Revision ID: 0015_cross_border_constraints
Revises: 0014_forecast_working_capital
"""
from alembic import op
import sqlalchemy as sa
revision = "0015_cross_border_constraints"
down_revision = "0014_forecast_working_capital"
branch_labels = None
depends_on = None

def upgrade() -> None:
    bind=op.get_bind(); existing=set(sa.inspect(bind).get_table_names())
    if "cross_border_constraints" not in existing:
        op.create_table("cross_border_constraints",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("source_country", sa.String(2), nullable=False), sa.Column("target_country", sa.String(2), nullable=False),
            sa.Column("transfer_type", sa.String(40), nullable=False), sa.Column("currency", sa.String(3), nullable=True),
            sa.Column("max_amount_reporting", sa.Numeric(20,4), nullable=True), sa.Column("withholding_tax_rate", sa.Numeric(12,8), nullable=False, server_default="0"),
            sa.Column("regulatory_status", sa.String(30), nullable=False, server_default="REVIEW_REQUIRED"), sa.Column("legal_status", sa.String(30), nullable=False, server_default="REVIEW_REQUIRED"),
            sa.Column("requires_tax_review", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("requires_legal_review", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("effective_from", sa.Date(), nullable=False), sa.Column("effective_to", sa.Date(), nullable=True), sa.Column("source_reference", sa.String(160), nullable=False, server_default="SYNTHETIC_MVP15"))
        for n in ["source_country","target_country","transfer_type","regulatory_status","legal_status"]: op.create_index(f"ix_cross_border_constraints_{n}","cross_border_constraints",[n])
def downgrade() -> None: op.drop_table("cross_border_constraints")
