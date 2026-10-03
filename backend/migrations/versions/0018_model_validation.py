"""MVP-18 independent model validation records."""
from alembic import op
import sqlalchemy as sa
revision="0018_model_validation"; down_revision="0017_security_controls"; branch_labels=None; depends_on=None

def upgrade():
    bind=op.get_bind(); existing=set(sa.inspect(bind).get_table_names())
    if "model_validation_records" not in existing:
        op.create_table("model_validation_records",
            sa.Column("id",sa.Integer(),primary_key=True), sa.Column("model_code",sa.String(100),nullable=False), sa.Column("validation_type",sa.String(50),nullable=False),
            sa.Column("metric_name",sa.String(80),nullable=False), sa.Column("metric_value",sa.Numeric(20,8),nullable=False), sa.Column("threshold_value",sa.Numeric(20,8),nullable=False),
            sa.Column("comparison",sa.String(4),nullable=False,server_default="LE"), sa.Column("status",sa.String(20),nullable=False),
            sa.Column("window_start",sa.Date(),nullable=True), sa.Column("window_end",sa.Date(),nullable=True), sa.Column("validated_by",sa.String(100),nullable=False,server_default="INDEPENDENT_MODEL_RISK"),
            sa.Column("created_at",sa.DateTime(),nullable=False), sa.Column("notes",sa.Text(),nullable=False,server_default=""))
        for n in ["model_code","validation_type","status","created_at"]: op.create_index(f"ix_model_validation_records_{n}","model_validation_records",[n])
def downgrade(): op.drop_table("model_validation_records")
