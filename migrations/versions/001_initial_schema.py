"""Initial TaskVault Schema

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-11-01 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # app_settings
    op.create_table(
        'app_settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('recovery_code_hash', sa.String(length=255), nullable=True),
        sa.Column('timezone', sa.String(length=64), nullable=False),
        sa.Column('theme', sa.String(length=32), nullable=False),
        sa.Column('lock_timeout_minutes', sa.Integer(), nullable=False),
        sa.Column('week_starts_on', sa.String(length=16), nullable=False),
        sa.Column('default_priority', sa.String(length=16), nullable=False),
        sa.Column('due_soon_days', sa.Integer(), nullable=False),
        sa.Column('daily_capacity_minutes', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )

    # login_attempts
    op.create_table(
        'login_attempts',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('attempted_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('succeeded', sa.Boolean(), nullable=False),
        sa.Column('source_fingerprint', sa.String(length=128), nullable=True),
        sa.Column('blocked_until', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_login_attempt_time', 'login_attempts', ['attempted_at'])
    op.create_index('idx_login_attempt_blocked', 'login_attempts', ['blocked_until'])

    # projects
    op.create_table(
        'projects',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('color', sa.String(length=32), nullable=True),
        sa.Column('icon', sa.String(length=32), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('archived_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_projects_status', 'projects', ['status'])
    op.create_index('idx_projects_name', 'projects', ['name'])

    # tags
    op.create_table(
        'tags',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=64), nullable=False),
        sa.Column('normalized_name', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('normalized_name'),
    )

    # recurrence_series
    op.create_table(
        'recurrence_series',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('priority', sa.String(length=16), nullable=False),
        sa.Column('project_id', sa.String(length=36), nullable=True),
        sa.Column('category', sa.String(length=64), nullable=True),
        sa.Column('estimated_minutes', sa.Integer(), nullable=True),
        sa.Column('frequency', sa.String(length=32), nullable=False),
        sa.Column('interval', sa.Integer(), nullable=False),
        sa.Column('weekdays', sa.Text(), nullable=True),
        sa.Column('day_of_month', sa.Integer(), nullable=True),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('next_occurrence_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('timezone', sa.String(length=64), nullable=False),
        sa.Column('is_paused', sa.Boolean(), nullable=False),
        sa.Column('missed_occurrence_policy', sa.String(length=32), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )

    # tasks
    op.create_table(
        'tasks',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('priority', sa.String(length=16), nullable=False),
        sa.Column('project_id', sa.String(length=36), nullable=True),
        sa.Column('parent_task_id', sa.String(length=36), nullable=True),
        sa.Column('category', sa.String(length=64), nullable=True),
        sa.Column('due_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('due_date_only', sa.Boolean(), nullable=False),
        sa.Column('start_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('planned_for_date', sa.Date(), nullable=True),
        sa.Column('estimated_minutes', sa.Integer(), nullable=True),
        sa.Column('actual_minutes', sa.Integer(), nullable=False),
        sa.Column('is_archived', sa.Boolean(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=False),
        sa.Column('recurrence_series_id', sa.String(length=36), nullable=True),
        sa.Column('occurrence_key', sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['parent_task_id'], ['tasks.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['recurrence_series_id'], ['recurrence_series.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_tasks_status', 'tasks', ['status'])
    op.create_index('idx_tasks_priority', 'tasks', ['priority'])
    op.create_index('idx_tasks_due_at', 'tasks', ['due_at'])
    op.create_index('idx_tasks_project_id', 'tasks', ['project_id'])
    op.create_index('idx_tasks_deleted_at', 'tasks', ['deleted_at'])
    op.create_index('idx_tasks_is_archived', 'tasks', ['is_archived'])
    op.create_index('idx_tasks_planned_date', 'tasks', ['planned_for_date'])

    # task_tags
    op.create_table(
        'task_tags',
        sa.Column('task_id', sa.String(length=36), nullable=False),
        sa.Column('tag_id', sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(['tag_id'], ['tags.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('task_id', 'tag_id'),
    )

    # checklist_items
    op.create_table(
        'checklist_items',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('task_id', sa.String(length=36), nullable=False),
        sa.Column('text', sa.String(length=255), nullable=False),
        sa.Column('is_completed', sa.Boolean(), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )

    # focus_sessions
    op.create_table(
        'focus_sessions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('task_id', sa.String(length=36), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_seconds', sa.Integer(), nullable=False),
        sa.Column('session_type', sa.String(length=32), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )

    # activity_log
    op.create_table(
        'activity_log',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('action', sa.String(length=64), nullable=False),
        sa.Column('entity_type', sa.String(length=32), nullable=False),
        sa.Column('entity_id', sa.String(length=36), nullable=True),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('activity_log')
    op.drop_table('focus_sessions')
    op.drop_table('checklist_items')
    op.drop_table('task_tags')
    op.drop_table('tasks')
    op.drop_table('recurrence_series')
    op.drop_table('tags')
    op.drop_table('projects')
    op.drop_table('login_attempts')
    op.drop_table('app_settings')

