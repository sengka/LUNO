"""project_invites tablosu (US-010, FR-021)

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-14

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0002'
down_revision: Union[str, Sequence[str], None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('project_invites',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('token', sa.String(length=64), nullable=False),
    sa.Column('project_id', sa.Integer(), nullable=False),
    sa.Column('created_by_id', sa.Integer(), nullable=True),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_project_invites_id'), 'project_invites', ['id'], unique=False)
    op.create_index(op.f('ix_project_invites_project_id'), 'project_invites', ['project_id'], unique=False)
    op.create_index(op.f('ix_project_invites_token'), 'project_invites', ['token'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_project_invites_token'), table_name='project_invites')
    op.drop_index(op.f('ix_project_invites_project_id'), table_name='project_invites')
    op.drop_index(op.f('ix_project_invites_id'), table_name='project_invites')
    op.drop_table('project_invites')
