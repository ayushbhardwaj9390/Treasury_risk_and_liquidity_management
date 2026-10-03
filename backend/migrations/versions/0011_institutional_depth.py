"""MVP-11 institutional counterparty, funding and survival-risk layer.

Revision ID: 0011_institutional_depth
Revises: 0008_live_ops
"""
from alembic import op
import sqlalchemy as sa

revision = "0011_institutional_depth"
down_revision = "0008_live_ops"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    existing = set(sa.inspect(bind).get_table_names())

    if "market_return_observations" not in existing:
        op.create_table(
            "market_return_observations",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("observation_date", sa.Date(), nullable=False),
            sa.Column("factor_type", sa.String(30), nullable=False, server_default="FX"),
            sa.Column("factor_key", sa.String(40), nullable=False),
            sa.Column("return_value", sa.Numeric(16, 10), nullable=False),
            sa.Column("source", sa.String(120), nullable=False, server_default="SYNTHETIC_HISTORICAL_MARKET"),
            sa.Column("approved", sa.Boolean(), nullable=False, server_default=sa.true()),
        )
        for name in ["observation_date", "factor_type", "factor_key", "approved"]:
            op.create_index(f"ix_market_return_observations_{name}", "market_return_observations", [name])

    if "counterparty_credit_metrics" not in existing:
        op.create_table(
            "counterparty_credit_metrics",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("counterparty", sa.String(120), nullable=False, unique=True),
            sa.Column("one_year_pd", sa.Numeric(12, 8), nullable=False, server_default="0.01"),
            sa.Column("lgd", sa.Numeric(12, 8), nullable=False, server_default="0.60"),
            sa.Column("funding_spread_bps", sa.Numeric(12, 4), nullable=False, server_default="100"),
            sa.Column("as_of", sa.Date(), nullable=False),
            sa.Column("source", sa.String(160), nullable=False, server_default="SYNTHETIC_CREDIT_RISK"),
            sa.Column("approved", sa.Boolean(), nullable=False, server_default=sa.false()),
        )
        for name in ["counterparty", "as_of", "approved"]:
            op.create_index(f"ix_counterparty_credit_metrics_{name}", "counterparty_credit_metrics", [name])

    if "treasury_risk_limits" not in existing:
        op.create_table(
            "treasury_risk_limits",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("limit_code", sa.String(100), nullable=False, unique=True),
            sa.Column("category", sa.String(60), nullable=False),
            sa.Column("metric_name", sa.String(120), nullable=False),
            sa.Column("comparator", sa.String(8), nullable=False, server_default="MAX"),
            sa.Column("threshold_value", sa.Numeric(24, 8), nullable=False),
            sa.Column("warning_utilization", sa.Numeric(12, 8), nullable=False, server_default="0.80"),
            sa.Column("currency", sa.String(3), nullable=True),
            sa.Column("effective_from", sa.Date(), nullable=False),
            sa.Column("effective_to", sa.Date(), nullable=True),
            sa.Column("owner", sa.String(120), nullable=False, server_default="GROUP_TREASURY_RISK"),
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        )
        for name in ["limit_code", "category", "metric_name", "active"]:
            op.create_index(f"ix_treasury_risk_limits_{name}", "treasury_risk_limits", [name])


def downgrade() -> None:
    bind = op.get_bind()
    existing = set(sa.inspect(bind).get_table_names())
    for table in ["treasury_risk_limits", "counterparty_credit_metrics", "market_return_observations"]:
        if table in existing:
            op.drop_table(table)
