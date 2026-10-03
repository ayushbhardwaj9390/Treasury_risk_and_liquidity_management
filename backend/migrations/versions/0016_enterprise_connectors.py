"""MVP-16 enterprise connector catalog."""
from alembic import op
import sqlalchemy as sa
revision="0016_enterprise_connectors"; down_revision="0015_cross_border_constraints"; branch_labels=None; depends_on=None

def upgrade():
    bind=op.get_bind(); existing=set(sa.inspect(bind).get_table_names())
    if "enterprise_connector_profiles" not in existing:
        op.create_table("enterprise_connector_profiles",
            sa.Column("id",sa.Integer(),primary_key=True), sa.Column("connector_code",sa.String(80),nullable=False), sa.Column("connector_type",sa.String(30),nullable=False),
            sa.Column("system_name",sa.String(120),nullable=False), sa.Column("protocol",sa.String(40),nullable=False,server_default="API"), sa.Column("auth_mode",sa.String(40),nullable=False,server_default="WORKLOAD_IDENTITY"),
            sa.Column("environment",sa.String(20),nullable=False,server_default="UAT"), sa.Column("status",sa.String(20),nullable=False,server_default="CONFIGURED"),
            sa.Column("last_success_at",sa.DateTime(),nullable=True), sa.Column("latency_ms",sa.Numeric(12,2),nullable=True), sa.Column("error_rate",sa.Numeric(12,8),nullable=False,server_default="0"),
            sa.Column("supports_idempotency",sa.Boolean(),nullable=False,server_default=sa.true()), sa.Column("supports_reconciliation",sa.Boolean(),nullable=False,server_default=sa.true()),
            sa.Column("data_contract_version",sa.String(30),nullable=False,server_default="1.0"), sa.UniqueConstraint("connector_code"))
        for n in ["connector_code","connector_type","environment","status"]: op.create_index(f"ix_enterprise_connector_profiles_{n}","enterprise_connector_profiles",[n])
def downgrade(): op.drop_table("enterprise_connector_profiles")
