"""create autotrade tables

Revision ID: 005
Revises: 004
Create Date: 2026-07-24

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade():
    # Create autotrade_bots table
    op.create_table(
        'autotrade_bots',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('ticker', sa.String(length=10), nullable=False),
        sa.Column('strategy', sa.String(length=50), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('position_size_pct', sa.Float(), nullable=False, server_default='0.10'),
        sa.Column('stop_loss_pct', sa.Float(), nullable=False, server_default='0.02'),
        sa.Column('take_profit_pct', sa.Float(), nullable=False, server_default='0.04'),
        sa.Column('daily_loss_limit_pct', sa.Float(), nullable=False, server_default='0.03'),
        sa.Column('max_positions', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('max_trades_per_day', sa.Integer(), nullable=False, server_default='10'),
        sa.Column('min_confidence', sa.Float(), nullable=False, server_default='55.0'),
        sa.Column('last_run_at', sa.DateTime(), nullable=True),
        sa.Column('last_signal', sa.String(length=10), nullable=True),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('total_trades', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('winning_trades', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_pnl', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_autotrade_bots_user_id', 'autotrade_bots', ['user_id'])
    op.create_index('ix_autotrade_bots_enabled', 'autotrade_bots', ['enabled'])

    # Create autotrade_logs table
    op.create_table(
        'autotrade_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('bot_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('ticker', sa.String(length=10), nullable=False),
        sa.Column('price', sa.Float(), nullable=True),
        sa.Column('signal_type', sa.String(length=10), nullable=False),
        sa.Column('signal_confidence', sa.Float(), nullable=True),
        sa.Column('signal_reason', sa.Text(), nullable=True),
        sa.Column('action_taken', sa.String(length=20), nullable=False),
        sa.Column('order_id', sa.String(), nullable=True),
        sa.Column('details', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['bot_id'], ['autotrade_bots.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_autotrade_logs_bot_id', 'autotrade_logs', ['bot_id'])
    op.create_index('ix_autotrade_logs_timestamp', 'autotrade_logs', ['timestamp'])


def downgrade():
    op.drop_index('ix_autotrade_logs_timestamp', 'autotrade_logs')
    op.drop_index('ix_autotrade_logs_bot_id', 'autotrade_logs')
    op.drop_table('autotrade_logs')
    op.drop_index('ix_autotrade_bots_enabled', 'autotrade_bots')
    op.drop_index('ix_autotrade_bots_user_id', 'autotrade_bots')
    op.drop_table('autotrade_bots')
