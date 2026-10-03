"""MVP-20 production-readiness gate."""
from alembic import op
import sqlalchemy as sa
revision="0020_production_readiness"; down_revision="0019_role_workflows"; branch_labels=None; depends_on=None

def upgrade():
    bind=op.get_bind(); existing=set(sa.inspect(bind).get_table_names())
    if "deployment_readiness_controls" not in existing:
        op.create_table("deployment_readiness_controls",
            sa.Column("id",sa.Integer(),primary_key=True), sa.Column("control_code",sa.String(100),nullable=False), sa.Column("category",sa.String(50),nullable=False),
            sa.Column("environment",sa.String(20),nullable=False,server_default="PRODUCTION"), sa.Column("required",sa.Boolean(),nullable=False,server_default=sa.true()),
            sa.Column("status",sa.String(20),nullable=False,server_default="NOT_READY"), sa.Column("evidence",sa.Text(),nullable=False,server_default=""), sa.Column("owner",sa.String(100),nullable=False,server_default="PLATFORM"),
            sa.Column("last_checked_at",sa.DateTime(),nullable=True), sa.UniqueConstraint("control_code"))
        for n in ["control_code","category","environment","status"]: op.create_index(f"ix_deployment_readiness_controls_{n}","deployment_readiness_controls",[n])
def downgrade(): op.drop_table("deployment_readiness_controls")
