"""add role column and activity_log table

Revision ID: 007
Revises: 006
Create Date: 2026-08-04
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '007'
down_revision = '006'
branch_labels = None
depends_on = None


def upgrade():
    # Add role + last_login_at to users
    op.add_column('users', sa.Column('role', sa.String(), nullable=False, server_default='user'))
    op.add_column('users', sa.Column('last_login_at', sa.DateTime(), nullable=True))

    # Create activity_log table
    op.create_table(
        'activity_log',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('category', sa.String(length=20), nullable=False),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('event_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_activity_log_user_id', 'activity_log', ['user_id'])
    op.create_index('ix_activity_log_created_at', 'activity_log', ['created_at'])
    op.create_index('ix_activity_log_category', 'activity_log', ['category'])

    # Create assistant_messages table (stores chat history per user)
    op.create_table(
        'assistant_messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role', sa.String(length=10), nullable=False),  # "user" | "assistant"
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_assistant_messages_user_id', 'assistant_messages', ['user_id'])
    op.create_index('ix_assistant_messages_created_at', 'assistant_messages', ['created_at'])


def downgrade():
    op.drop_index('ix_assistant_messages_created_at', 'assistant_messages')
    op.drop_index('ix_assistant_messages_user_id', 'assistant_messages')
    op.drop_table('assistant_messages')
    op.drop_index('ix_activity_log_category', 'activity_log')
    op.drop_index('ix_activity_log_created_at', 'activity_log')
    op.drop_index('ix_activity_log_user_id', 'activity_log')
    op.drop_table('activity_log')
    op.drop_column('users', 'last_login_at')
    op.drop_column('users', 'role')
