"""MVP-7 institutional treasury risk layer.

Revision ID: 0007_institutional
Revises: 0006_predictive
"""
from alembic import op
import sqlalchemy as sa

revision = "0007_institutional"
down_revision = "0006_predictive"
branch_labels = None
depends_on = None


def upgrade() -> None:
    existing = set(sa.inspect(op.get_bind()).get_table_names())
    if "derivative_valuation_terms" in existing:
        return
    op.create_table(
        "derivative_valuation_terms",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("derivative_position_id", sa.Integer(), sa.ForeignKey("derivative_positions.id"), nullable=False, unique=True),
        sa.Column("model_type", sa.String(50), nullable=False),
        sa.Column("currency_pair", sa.String(7)),
        sa.Column("contracted_rate", sa.Numeric(20, 10)),
        sa.Column("strike", sa.Numeric(20, 10)),
        sa.Column("option_type", sa.String(8)),
        sa.Column("fixed_rate", sa.Numeric(12, 8)),
        sa.Column("floating_spread_bps", sa.Numeric(12, 4), nullable=False, server_default="0"),
        sa.Column("payment_frequency_per_year", sa.Integer(), nullable=False, server_default="4"),
        sa.Column("notional_currency", sa.String(3)),
        sa.Column("source_reference", sa.String(160), nullable=False),
    )
    op.create_table(
        "market_curve_points",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("curve_name", sa.String(100), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("curve_type", sa.String(30), nullable=False),
        sa.Column("tenor_days", sa.Integer(), nullable=False),
        sa.Column("zero_rate", sa.Numeric(12, 8), nullable=False),
        sa.Column("as_of", sa.DateTime(), nullable=False),
        sa.Column("source", sa.String(120), nullable=False),
    )
    op.create_table(
        "volatility_quotes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("asset_class", sa.String(30), nullable=False),
        sa.Column("underlying", sa.String(20), nullable=False),
        sa.Column("tenor_days", sa.Integer(), nullable=False),
        sa.Column("quote_type", sa.String(30), nullable=False),
        sa.Column("volatility", sa.Numeric(12, 8), nullable=False),
        sa.Column("as_of", sa.DateTime(), nullable=False),
        sa.Column("source", sa.String(120), nullable=False),
    )
    op.create_table(
        "legal_netting_sets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("netting_set_code", sa.String(80), nullable=False, unique=True),
        sa.Column("counterparty", sa.String(120), nullable=False),
        sa.Column("agreement_type", sa.String(40), nullable=False),
        sa.Column("governing_law", sa.String(80), nullable=False),
        sa.Column("close_out_netting_enforceable", sa.Boolean(), nullable=False),
        sa.Column("legal_opinion_status", sa.String(30), nullable=False),
        sa.Column("collateral_agreement_id", sa.Integer(), sa.ForeignKey("collateral_agreements.id")),
        sa.Column("last_legal_review_date", sa.Date()),
    )
    op.create_table(
        "netting_set_trades",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("netting_set_id", sa.Integer(), sa.ForeignKey("legal_netting_sets.id"), nullable=False),
        sa.Column("derivative_position_id", sa.Integer(), sa.ForeignKey("derivative_positions.id"), nullable=False, unique=True),
    )
    op.create_table(
        "model_deployments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("model_code", sa.String(100), nullable=False),
        sa.Column("version", sa.String(40), nullable=False),
        sa.Column("deployment_role", sa.String(20), nullable=False),
        sa.Column("approval_status", sa.String(24), nullable=False),
        sa.Column("effective_from", sa.DateTime(), nullable=False),
        sa.Column("approved_by", sa.String(120)),
        sa.Column("promotion_threshold_pct", sa.Numeric(12, 6), nullable=False),
        sa.Column("notes", sa.String(500), nullable=False),
    )
    op.create_table(
        "resilience_controls",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("component_name", sa.String(120), nullable=False, unique=True),
        sa.Column("criticality_tier", sa.String(20), nullable=False),
        sa.Column("rto_minutes", sa.Integer(), nullable=False),
        sa.Column("rpo_minutes", sa.Integer(), nullable=False),
        sa.Column("multi_region", sa.Boolean(), nullable=False),
        sa.Column("last_dr_test_at", sa.DateTime()),
        sa.Column("last_dr_test_result", sa.String(20), nullable=False),
        sa.Column("owner", sa.String(120), nullable=False),
    )


def downgrade() -> None:
    for table in [
        "resilience_controls", "model_deployments", "netting_set_trades", "legal_netting_sets",
        "volatility_quotes", "market_curve_points", "derivative_valuation_terms",
    ]:
        op.drop_table(table)
