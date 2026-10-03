"""Production Phase 1 v2: shadow promotion, data-quality SLAs and parallel-run validation."""
from alembic import op
import sqlalchemy as sa

revision = "0024_parallel_validation"
down_revision = "0023_real_data_integration"
branch_labels = None
depends_on = None


def _idx(table: str, columns: list[str]):
    for column in columns:
        op.create_index(f"ix_{table}_{column}", table, [column])


def upgrade():
    existing = set(sa.inspect(op.get_bind()).get_table_names())
    if "source_authority_policies" not in existing:
        op.create_table(
            "source_authority_policies",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("connector_code", sa.String(80), nullable=False),
            sa.Column("data_domain", sa.String(60), nullable=False),
            sa.Column("mode", sa.String(20), nullable=False, server_default="SHADOW"),
            sa.Column("evidence", sa.Text(), nullable=False, server_default=""),
            sa.Column("approved_by", sa.String(100), nullable=True),
            sa.Column("approved_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("connector_code", "data_domain", name="uq_source_authority_policy"),
        )
        _idx("source_authority_policies", ["connector_code", "data_domain", "mode", "updated_at"])

    if "integration_shadow_records" not in existing:
        op.create_table(
            "integration_shadow_records",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("connector_code", sa.String(80), nullable=False),
            sa.Column("data_domain", sa.String(60), nullable=False),
            sa.Column("source_record_id", sa.String(180), nullable=False),
            sa.Column("mapped_internal_id", sa.Integer(), nullable=True),
            sa.Column("target_table", sa.String(80), nullable=False),
            sa.Column("currency", sa.String(3), nullable=True),
            sa.Column("amount", sa.Numeric(24, 6), nullable=True),
            sa.Column("as_of", sa.DateTime(), nullable=True),
            sa.Column("payload_hash", sa.String(64), nullable=False),
            sa.Column("payload_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("status", sa.String(24), nullable=False, server_default="SHADOW"),
            sa.Column("ingested_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("connector_code", "data_domain", "source_record_id", "payload_hash", name="uq_integration_shadow_source_hash"),
        )
        _idx("integration_shadow_records", ["connector_code", "data_domain", "source_record_id", "mapped_internal_id", "target_table", "currency", "as_of", "payload_hash", "status", "ingested_at"])

    if "data_quality_sla_results" not in existing:
        op.create_table(
            "data_quality_sla_results",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("connector_code", sa.String(80), nullable=False),
            sa.Column("data_domain", sa.String(60), nullable=False),
            sa.Column("as_of", sa.DateTime(), nullable=False),
            sa.Column("timeliness_score", sa.Numeric(8, 6), nullable=False, server_default="0"),
            sa.Column("completeness_score", sa.Numeric(8, 6), nullable=False, server_default="0"),
            sa.Column("validity_score", sa.Numeric(8, 6), nullable=False, server_default="0"),
            sa.Column("uniqueness_score", sa.Numeric(8, 6), nullable=False, server_default="0"),
            sa.Column("reconciliation_score", sa.Numeric(8, 6), nullable=False, server_default="0"),
            sa.Column("overall_score", sa.Numeric(8, 6), nullable=False, server_default="0"),
            sa.Column("status", sa.String(20), nullable=False, server_default="WATCH"),
            sa.Column("breaches_json", sa.Text(), nullable=False, server_default="[]"),
        )
        _idx("data_quality_sla_results", ["connector_code", "data_domain", "as_of", "status"])

    if "parallel_run_observations" not in existing:
        op.create_table(
            "parallel_run_observations",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("connector_code", sa.String(80), nullable=False),
            sa.Column("data_domain", sa.String(60), nullable=False),
            sa.Column("observation_date", sa.Date(), nullable=False),
            sa.Column("metric_name", sa.String(100), nullable=False),
            sa.Column("incumbent_value", sa.Numeric(24, 6), nullable=False),
            sa.Column("platform_value", sa.Numeric(24, 6), nullable=False),
            sa.Column("absolute_difference", sa.Numeric(24, 6), nullable=False, server_default="0"),
            sa.Column("percentage_difference", sa.Numeric(12, 8), nullable=False, server_default="0"),
            sa.Column("tolerance_pct", sa.Numeric(12, 8), nullable=False, server_default="0"),
            sa.Column("status", sa.String(20), nullable=False, server_default="PASS"),
            sa.Column("evidence", sa.Text(), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("connector_code", "data_domain", "observation_date", "metric_name", name="uq_parallel_run_observation"),
        )
        _idx("parallel_run_observations", ["connector_code", "data_domain", "observation_date", "metric_name", "status", "created_at"])

    # Add accountable resolution fields to quarantine if they are not already present.
    cols = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("integration_quarantine")}
    if "resolved_by" not in cols:
        op.add_column("integration_quarantine", sa.Column("resolved_by", sa.String(100), nullable=True))
    if "resolved_at" not in cols:
        op.add_column("integration_quarantine", sa.Column("resolved_at", sa.DateTime(), nullable=True))


def downgrade():
    cols = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("integration_quarantine")}
    if "resolved_at" in cols:
        op.drop_column("integration_quarantine", "resolved_at")
    if "resolved_by" in cols:
        op.drop_column("integration_quarantine", "resolved_by")
    for table in ["parallel_run_observations", "data_quality_sla_results", "integration_shadow_records", "source_authority_policies"]:
        op.drop_table(table)
