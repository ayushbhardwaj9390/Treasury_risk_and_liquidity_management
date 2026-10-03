"""MVP-19 role-specific investigation workflows."""
from alembic import op
import sqlalchemy as sa
revision="0019_role_workflows"; down_revision="0018_model_validation"; branch_labels=None; depends_on=None

def upgrade():
    bind=op.get_bind(); existing=set(sa.inspect(bind).get_table_names())
    if "investigation_cases" not in existing:
        op.create_table("investigation_cases",
            sa.Column("id",sa.Integer(),primary_key=True), sa.Column("case_type",sa.String(50),nullable=False), sa.Column("severity",sa.String(20),nullable=False),
            sa.Column("status",sa.String(24),nullable=False,server_default="OPEN"), sa.Column("owner_role",sa.String(50),nullable=False), sa.Column("entity_id",sa.Integer(),sa.ForeignKey("legal_entities.id"),nullable=True),
            sa.Column("reference",sa.String(160),nullable=False), sa.Column("title",sa.String(200),nullable=False), sa.Column("details",sa.Text(),nullable=False,server_default=""),
            sa.Column("opened_at",sa.DateTime(),nullable=False), sa.Column("updated_at",sa.DateTime(),nullable=False), sa.UniqueConstraint("reference"))
        for n in ["case_type","severity","status","owner_role","entity_id","reference","opened_at","updated_at"]: op.create_index(f"ix_investigation_cases_{n}","investigation_cases",[n])
def downgrade(): op.drop_table("investigation_cases")
