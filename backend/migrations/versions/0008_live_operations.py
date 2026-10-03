"""MVP-8 live treasury operations layer.

Revision ID: 0008_live_ops
Revises: 0007_institutional
"""
from alembic import op
import sqlalchemy as sa

revision = "0008_live_ops"
down_revision = "0007_institutional"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = set(inspector.get_table_names())

    cash_cols = {c["name"] for c in inspector.get_columns("cash_flows")} if "cash_flows" in existing else set()
    if "cash_flows" in existing and "source_reference" not in cash_cols:
        op.add_column("cash_flows", sa.Column("source_reference", sa.String(180), nullable=True))
        op.create_index("ix_cash_flows_source_reference", "cash_flows", ["source_reference"])

    if "treasury_events" not in existing:
        op.create_table(
            "treasury_events",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("idempotency_key", sa.String(180), nullable=False, unique=True),
            sa.Column("event_type", sa.String(60), nullable=False),
            sa.Column("source_system", sa.String(120), nullable=False),
            sa.Column("connector_name", sa.String(120), nullable=False),
            sa.Column("entity_id", sa.Integer(), sa.ForeignKey("legal_entities.id"), nullable=True),
            sa.Column("external_reference", sa.String(180), nullable=True),
            sa.Column("sequence_no", sa.Integer(), nullable=True),
            sa.Column("schema_version", sa.String(20), nullable=False, server_default="1.0"),
            sa.Column("event_time", sa.DateTime(), nullable=False),
            sa.Column("received_at", sa.DateTime(), nullable=False),
            sa.Column("payload_hash", sa.String(64), nullable=False),
            sa.Column("payload_json", sa.Text(), nullable=False),
            sa.Column("processing_status", sa.String(40), nullable=False, server_default="RECEIVED"),
            sa.Column("processing_error", sa.String(500), nullable=False, server_default=""),
            sa.Column("replay_count", sa.Integer(), nullable=False, server_default="0"),
        )
        for name in ["idempotency_key", "event_type", "source_system", "connector_name", "entity_id", "external_reference", "event_time", "received_at", "payload_hash", "processing_status"]:
            op.create_index(f"ix_treasury_events_{name}", "treasury_events", [name])

    if "connector_checkpoints" not in existing:
        op.create_table(
            "connector_checkpoints",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("connector_name", sa.String(120), nullable=False, unique=True),
            sa.Column("source_system", sa.String(120), nullable=False),
            sa.Column("last_sequence_no", sa.Integer(), nullable=True),
            sa.Column("last_event_time", sa.DateTime(), nullable=True),
            sa.Column("last_received_at", sa.DateTime(), nullable=True),
            sa.Column("accepted_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("duplicate_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("quarantined_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("failed_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("status", sa.String(24), nullable=False, server_default="ACTIVE"),
        )
        op.create_index("ix_connector_checkpoints_connector_name", "connector_checkpoints", ["connector_name"])
        op.create_index("ix_connector_checkpoints_source_system", "connector_checkpoints", ["source_system"])
        op.create_index("ix_connector_checkpoints_last_event_time", "connector_checkpoints", ["last_event_time"])
        op.create_index("ix_connector_checkpoints_status", "connector_checkpoints", ["status"])

    if "execution_messages" not in existing:
        op.create_table(
            "execution_messages",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("message_id", sa.String(80), nullable=False, unique=True),
            sa.Column("proposal_id", sa.Integer(), sa.ForeignKey("transaction_proposals.id"), nullable=False),
            sa.Column("connector_name", sa.String(120), nullable=False),
            sa.Column("idempotency_key", sa.String(180), nullable=False, unique=True),
            sa.Column("payload_hash", sa.String(64), nullable=False),
            sa.Column("payload_json", sa.Text(), nullable=False),
            sa.Column("signature", sa.String(128), nullable=False, server_default="DEMO_UNVERIFIED"),
            sa.Column("status", sa.String(32), nullable=False, server_default="QUEUED"),
            sa.Column("created_by", sa.String(80), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("sent_at", sa.DateTime(), nullable=True),
            sa.Column("acknowledged_at", sa.DateTime(), nullable=True),
            sa.Column("external_reference", sa.String(180), nullable=True),
            sa.Column("acknowledgement_detail", sa.String(500), nullable=False, server_default=""),
        )
        for name in ["message_id", "proposal_id", "connector_name", "idempotency_key", "status", "created_by", "created_at", "external_reference"]:
            op.create_index(f"ix_execution_messages_{name}", "execution_messages", [name])

    if "live_treasury_alerts" not in existing:
        op.create_table(
            "live_treasury_alerts",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("alert_key", sa.String(180), nullable=False, unique=True),
            sa.Column("category", sa.String(60), nullable=False),
            sa.Column("severity", sa.String(20), nullable=False),
            sa.Column("title", sa.String(180), nullable=False),
            sa.Column("message", sa.String(800), nullable=False),
            sa.Column("source_event_id", sa.Integer(), sa.ForeignKey("treasury_events.id"), nullable=True),
            sa.Column("status", sa.String(24), nullable=False, server_default="OPEN"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("last_seen_at", sa.DateTime(), nullable=False),
            sa.Column("acknowledged_by", sa.String(80), nullable=True),
            sa.Column("acknowledged_at", sa.DateTime(), nullable=True),
        )
        for name in ["alert_key", "category", "severity", "source_event_id", "status", "created_at", "last_seen_at"]:
            op.create_index(f"ix_live_treasury_alerts_{name}", "live_treasury_alerts", [name])


def downgrade() -> None:
    bind = op.get_bind()
    existing = set(sa.inspect(bind).get_table_names())
    for table in ["live_treasury_alerts", "execution_messages", "connector_checkpoints", "treasury_events"]:
        if table in existing:
            op.drop_table(table)
    if "cash_flows" in existing:
        cols = {c["name"] for c in sa.inspect(bind).get_columns("cash_flows")}
        if "source_reference" in cols:
            try:
                op.drop_index("ix_cash_flows_source_reference", table_name="cash_flows")
            except Exception:
                pass
            op.drop_column("cash_flows", "source_reference")
