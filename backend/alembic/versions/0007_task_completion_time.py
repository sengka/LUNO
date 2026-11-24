"""Raporlar için tamamlanma zamanını düzenleme zamanından ayır (#241).

Revision ID: 0007
Revises: 0006
"""
from alembic import op
import sqlalchemy as sa

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade():
    # Eski bitiş zamanı geri üretilemez; mevcut tahmini sonraki düzenlemelerden koru.
    op.add_column("tasks", sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True))
    op.execute(sa.text("UPDATE tasks SET completed_at = updated_at WHERE status = 'DONE'"))


def downgrade():
    op.drop_column("tasks", "completed_at")
