"""Production Phase 1: real-data integration, lineage and reconciliation."""
from alembic import op
import sqlalchemy as sa

revision = "0023_real_data_integration"
down_revision = "0020_production_readiness"
branch_labels = None
depends_on = None


def _idx(table: str, columns: list[str]):
    for column in columns:
        op.create_index(f"ix_{table}_{column}", table, [column])


def upgrade():
    existing = set(sa.inspect(op.get_bind()).get_table_names())
    if "external_reference_maps" not in existing:
        op.create_table(
            "external_reference_maps",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("connector_code", sa.String(80), nullable=False),
            sa.Column("object_type", sa.String(40), nullable=False),
            sa.Column("external_id", sa.String(180), nullable=False),
            sa.Column("internal_id", sa.Integer(), nullable=True),
            sa.Column("internal_code", sa.String(180), nullable=True),
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("source_reference", sa.String(180), nullable=False, server_default="PHASE1_MAPPING"),
            sa.UniqueConstraint("connector_code", "object_type", "external_id", name="uq_external_reference_map"),
        )
        _idx("external_reference_maps", ["connector_code", "object_type", "external_id", "internal_id", "active"])

    if "integration_runs" not in existing:
        op.create_table(
            "integration_runs",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("connector_code", sa.String(80), nullable=False),
            sa.Column("run_type", sa.String(50), nullable=False),
            sa.Column("status", sa.String(30), nullable=False, server_default="STARTED"),
            sa.Column("started_at", sa.DateTime(), nullable=False),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            sa.Column("records_received", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("records_applied", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("records_quarantined", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("source_total", sa.Numeric(24,6), nullable=False, server_default="0"),
            sa.Column("target_total", sa.Numeric(24,6), nullable=False, server_default="0"),
            sa.Column("difference", sa.Numeric(24,6), nullable=False, server_default="0"),
            sa.Column("watermark", sa.String(180), nullable=True),
            sa.Column("payload_hash", sa.String(64), nullable=True),
            sa.Column("error_detail", sa.Text(), nullable=False, server_default=""),
        )
        _idx("integration_runs", ["connector_code", "run_type", "status", "started_at", "payload_hash"])

    if "data_lineage_records" not in existing:
        op.create_table(
            "data_lineage_records",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("connector_code", sa.String(80), nullable=False),
            sa.Column("source_system", sa.String(120), nullable=False),
            sa.Column("source_object_type", sa.String(60), nullable=False),
            sa.Column("source_record_id", sa.String(180), nullable=False),
            sa.Column("target_table", sa.String(80), nullable=False),
            sa.Column("target_record_id", sa.Integer(), nullable=True),
            sa.Column("source_timestamp", sa.DateTime(), nullable=True),
            sa.Column("ingested_at", sa.DateTime(), nullable=False),
            sa.Column("payload_hash", sa.String(64), nullable=False),
            sa.Column("schema_version", sa.String(30), nullable=False, server_default="1.0"),
            sa.Column("reconciliation_status", sa.String(30), nullable=False, server_default="PENDING"),
            sa.UniqueConstraint("connector_code", "source_object_type", "source_record_id", "payload_hash", name="uq_data_lineage_source_hash"),
        )
        _idx("data_lineage_records", ["connector_code", "source_system", "source_object_type", "source_record_id", "target_table", "target_record_id", "source_timestamp", "ingested_at", "payload_hash", "reconciliation_status"])

    if "integration_quarantine" not in existing:
        op.create_table(
            "integration_quarantine",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("connector_code", sa.String(80), nullable=False),
            sa.Column("record_type", sa.String(60), nullable=False),
            sa.Column("source_reference", sa.String(180), nullable=False),
            sa.Column("reason_code", sa.String(80), nullable=False),
            sa.Column("reason_detail", sa.Text(), nullable=False, server_default=""),
            sa.Column("payload_json", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("quarantined_at", sa.DateTime(), nullable=False),
            sa.Column("resolved", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("resolution", sa.Text(), nullable=False, server_default=""),
        )
        _idx("integration_quarantine", ["connector_code", "record_type", "source_reference", "reason_code", "quarantined_at", "resolved"])

    if "integration_certification_controls" not in existing:
        op.create_table(
            "integration_certification_controls",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("connector_code", sa.String(80), nullable=False),
            sa.Column("control_code", sa.String(100), nullable=False),
            sa.Column("required", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("status", sa.String(24), nullable=False, server_default="NOT_TESTED"),
            sa.Column("evidence", sa.Text(), nullable=False, server_default=""),
            sa.Column("owner", sa.String(100), nullable=False, server_default="TREASURY_TECH"),
            sa.Column("last_checked_at", sa.DateTime(), nullable=True),
            sa.UniqueConstraint("connector_code", "control_code", name="uq_integration_cert_control"),
        )
        _idx("integration_certification_controls", ["connector_code", "control_code", "status"])

    if "bank_transaction_records" not in existing:
        op.create_table(
            "bank_transaction_records",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("connector_code", sa.String(80), nullable=False),
            sa.Column("bank_account_id", sa.Integer(), sa.ForeignKey("bank_accounts.id"), nullable=True),
            sa.Column("external_account_id", sa.String(180), nullable=False),
            sa.Column("source_record_id", sa.String(180), nullable=False),
            sa.Column("booking_date", sa.Date(), nullable=False),
            sa.Column("value_date", sa.Date(), nullable=True),
            sa.Column("currency", sa.String(3), nullable=False),
            sa.Column("amount", sa.Numeric(24,6), nullable=False),
            sa.Column("credit_debit", sa.String(8), nullable=False),
            sa.Column("counterparty", sa.String(180), nullable=False, server_default=""),
            sa.Column("reference", sa.String(240), nullable=False, server_default=""),
            sa.Column("status", sa.String(30), nullable=False, server_default="BOOKED"),
            sa.Column("payload_hash", sa.String(64), nullable=False),
            sa.Column("ingested_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("connector_code", "source_record_id", name="uq_bank_transaction_source"),
        )
        _idx("bank_transaction_records", ["connector_code", "bank_account_id", "external_account_id", "source_record_id", "booking_date", "value_date", "currency", "credit_debit", "reference", "status", "payload_hash", "ingested_at"])

    if "erp_journal_records" not in existing:
        op.create_table(
            "erp_journal_records",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("connector_code", sa.String(80), nullable=False),
            sa.Column("legal_entity_id", sa.Integer(), sa.ForeignKey("legal_entities.id"), nullable=True),
            sa.Column("source_record_id", sa.String(180), nullable=False),
            sa.Column("posting_date", sa.Date(), nullable=False),
            sa.Column("currency", sa.String(3), nullable=False),
            sa.Column("amount", sa.Numeric(24,6), nullable=False),
            sa.Column("counterparty", sa.String(180), nullable=False, server_default=""),
            sa.Column("reference", sa.String(240), nullable=False, server_default=""),
            sa.Column("document_type", sa.String(50), nullable=False, server_default="BANK_GL"),
            sa.Column("payload_hash", sa.String(64), nullable=False),
            sa.Column("ingested_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("connector_code", "source_record_id", name="uq_erp_journal_source"),
        )
        _idx("erp_journal_records", ["connector_code", "legal_entity_id", "source_record_id", "posting_date", "currency", "reference", "payload_hash", "ingested_at"])

    if "reconciliation_exception_records" not in existing:
        op.create_table(
            "reconciliation_exception_records",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("reconciliation_run_id", sa.Integer(), sa.ForeignKey("reconciliation_runs.id"), nullable=False),
            sa.Column("bank_transaction_id", sa.Integer(), sa.ForeignKey("bank_transaction_records.id"), nullable=True),
            sa.Column("erp_journal_id", sa.Integer(), sa.ForeignKey("erp_journal_records.id"), nullable=True),
            sa.Column("exception_type", sa.String(60), nullable=False),
            sa.Column("amount_difference", sa.Numeric(24,6), nullable=False, server_default="0"),
            sa.Column("detail", sa.Text(), nullable=False, server_default=""),
            sa.Column("status", sa.String(24), nullable=False, server_default="OPEN"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )
        _idx("reconciliation_exception_records", ["reconciliation_run_id", "bank_transaction_id", "erp_journal_id", "exception_type", "status", "created_at"])


def downgrade():
    for table in [
        "reconciliation_exception_records", "erp_journal_records", "bank_transaction_records",
        "integration_certification_controls", "integration_quarantine", "data_lineage_records",
        "integration_runs", "external_reference_maps",
    ]:
        op.drop_table(table)
