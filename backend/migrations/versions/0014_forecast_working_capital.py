"""MVP-14 forecast accuracy and working-capital intelligence.

Revision ID: 0014_forecast_working_capital
Revises: 0011_institutional_depth
"""
from alembic import op
import sqlalchemy as sa

revision = "0014_forecast_working_capital"
down_revision = "0011_institutional_depth"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    existing = set(sa.inspect(bind).get_table_names())
    if "forecast_performance_records" not in existing:
        op.create_table(
            "forecast_performance_records",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("entity_id", sa.Integer(), sa.ForeignKey("legal_entities.id"), nullable=False),
            sa.Column("forecast_date", sa.Date(), nullable=False),
            sa.Column("target_date", sa.Date(), nullable=False),
            sa.Column("flow_type", sa.String(20), nullable=False),
            sa.Column("counterparty", sa.String(160), nullable=False),
            sa.Column("currency", sa.String(3), nullable=False),
            sa.Column("forecast_amount", sa.Numeric(20, 4), nullable=False),
            sa.Column("actual_amount", sa.Numeric(20, 4), nullable=False),
            sa.Column("model_code", sa.String(100), nullable=False, server_default="TREASURY_CASH_FORECAST"),
            sa.Column("horizon_days", sa.Integer(), nullable=False, server_default="7"),
            sa.Column("source_reference", sa.String(160), nullable=False, server_default="SYNTHETIC_FORECAST_HISTORY"),
        )
        for name in ["entity_id", "forecast_date", "target_date", "flow_type", "counterparty", "currency", "model_code", "horizon_days"]:
            op.create_index(f"ix_forecast_performance_records_{name}", "forecast_performance_records", [name])

    if "working_capital_observations" not in existing:
        op.create_table(
            "working_capital_observations",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("entity_id", sa.Integer(), sa.ForeignKey("legal_entities.id"), nullable=False),
            sa.Column("period_end", sa.Date(), nullable=False),
            sa.Column("currency", sa.String(3), nullable=False),
            sa.Column("revenue", sa.Numeric(20, 4), nullable=False),
            sa.Column("cogs", sa.Numeric(20, 4), nullable=False),
            sa.Column("receivables_balance", sa.Numeric(20, 4), nullable=False),
            sa.Column("payables_balance", sa.Numeric(20, 4), nullable=False),
            sa.Column("inventory_balance", sa.Numeric(20, 4), nullable=False),
            sa.Column("source_reference", sa.String(160), nullable=False, server_default="SYNTHETIC_WORKING_CAPITAL"),
        )
        for name in ["entity_id", "period_end", "currency"]:
            op.create_index(f"ix_working_capital_observations_{name}", "working_capital_observations", [name])


def downgrade() -> None:
    bind = op.get_bind()
    existing = set(sa.inspect(bind).get_table_names())
    for table in ["working_capital_observations", "forecast_performance_records"]:
        if table in existing:
            op.drop_table(table)
