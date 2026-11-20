"""sprints ve notifications tabloları, tasks.sprint_id bağlantısı (#248)

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-19

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0006'
down_revision: str | Sequence[str] | None = '0005'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('sprints',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('project_id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('goal', sa.Text(), nullable=True),
    sa.Column('start_date', sa.Date(), nullable=False),
    sa.Column('end_date', sa.Date(), nullable=False),
    sa.Column('capacity_points', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint('capacity_points IS NULL OR capacity_points > 0', name='ck_sprints_capacity_positive'),
    sa.CheckConstraint('end_date >= start_date', name='ck_sprints_end_after_start'),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_sprints_project_id'), 'sprints', ['project_id'], unique=False)

    op.create_table('notifications',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('type', sa.Enum('TASK_ASSIGNED', 'COMMENT_ADDED', 'DUE_DATE_SOON', 'TASK_STALE', 'TASK_PENDING_APPROVAL', 'TASK_APPROVED', 'TASK_REJECTED', name='ck_notifications_type', native_enum=False, create_constraint=True, length=30), nullable=False),
    sa.Column('message', sa.String(length=500), nullable=False),
    sa.Column('project_id', sa.Integer(), nullable=True),
    sa.Column('task_id', sa.Integer(), nullable=True),
    sa.Column('is_read', sa.Boolean(), server_default=sa.false(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_notifications_project_id'), 'notifications', ['project_id'], unique=False)
    op.create_index(op.f('ix_notifications_task_id'), 'notifications', ['task_id'], unique=False)
    op.create_index('ix_notifications_user_id_created_at', 'notifications', ['user_id', 'created_at'], unique=False)
    op.create_index('ix_notifications_user_id_is_read', 'notifications', ['user_id', 'is_read'], unique=False)

    # tasks.sprint_id şimdiye kadar yabancı anahtarsızdı ve sprints tablosu yoktu; bu yüzden
    # içindeki değerler hiçbir sprinte bağlanamaz. Görevlerin kendisine dokunmadan yalnızca
    # bu boşta kalan değerler null yapılır, sonra yabancı anahtar eklenir.
    op.execute('UPDATE tasks SET sprint_id = NULL WHERE sprint_id IS NOT NULL')
    # SQLite ALTER TABLE ile kısıt ekleyemediği için batch modu (tabloyu yeniden kurar).
    with op.batch_alter_table('tasks') as batch_op:
        batch_op.create_foreign_key(
            'fk_tasks_sprint_id_sprints', 'sprints', ['sprint_id'], ['id'], ondelete='SET NULL'
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('tasks') as batch_op:
        batch_op.drop_constraint('fk_tasks_sprint_id_sprints', type_='foreignkey')
    op.drop_index('ix_notifications_user_id_is_read', table_name='notifications')
    op.drop_index('ix_notifications_user_id_created_at', table_name='notifications')
    op.drop_index(op.f('ix_notifications_task_id'), table_name='notifications')
    op.drop_index(op.f('ix_notifications_project_id'), table_name='notifications')
    op.drop_table('notifications')
    op.drop_index(op.f('ix_sprints_project_id'), table_name='sprints')
    op.drop_table('sprints')
