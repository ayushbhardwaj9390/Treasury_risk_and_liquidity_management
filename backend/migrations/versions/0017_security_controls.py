"""MVP-17 enterprise security controls."""
from alembic import op
import sqlalchemy as sa
revision="0017_security_controls"; down_revision="0016_enterprise_connectors"; branch_labels=None; depends_on=None

def upgrade():
    bind=op.get_bind(); existing=set(sa.inspect(bind).get_table_names())
    if "security_control_records" not in existing:
        op.create_table("security_control_records",
            sa.Column("id",sa.Integer(),primary_key=True), sa.Column("control_code",sa.String(100),nullable=False), sa.Column("domain",sa.String(50),nullable=False),
            sa.Column("required",sa.Boolean(),nullable=False,server_default=sa.true()), sa.Column("status",sa.String(20),nullable=False,server_default="NOT_TESTED"),
            sa.Column("evidence",sa.Text(),nullable=False,server_default=""), sa.Column("owner",sa.String(100),nullable=False,server_default="SECURITY"), sa.Column("last_tested_at",sa.DateTime(),nullable=True),
            sa.UniqueConstraint("control_code"))
        for n in ["control_code","domain","status"]: op.create_index(f"ix_security_control_records_{n}","security_control_records",[n])
def downgrade(): op.drop_table("security_control_records")
