"""create autopilot tables

Revision ID: 006
Revises: 005
Create Date: 2026-07-24

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None


def upgrade():
    # ---- autopilot_config ----
    op.create_table(
        'autopilot_config',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('market_type', sa.String(length=10), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('capital', sa.Float(), nullable=False, server_default='10000.0'),
        sa.Column('daily_profit_target', sa.Float(), nullable=False, server_default='100.0'),
        sa.Column('daily_loss_limit', sa.Float(), nullable=False, server_default='200.0'),
        sa.Column('max_concurrent_positions', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('max_position_size_pct', sa.Float(), nullable=False, server_default='0.34'),
        sa.Column('take_profit_pct', sa.Float(), nullable=False, server_default='0.03'),
        sa.Column('stop_loss_pct', sa.Float(), nullable=False, server_default='0.02'),
        sa.Column('min_price', sa.Float(), nullable=False, server_default='0.50'),
        sa.Column('max_price', sa.Float(), nullable=False, server_default='5.0'),
        sa.Column('min_change_pct', sa.Float(), nullable=False, server_default='3.0'),
        sa.Column('min_volume_ratio', sa.Float(), nullable=False, server_default='1.5'),
        sa.Column('max_candidates', sa.Integer(), nullable=False, server_default='15'),
        sa.Column('use_llm', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('llm_min_confidence', sa.Float(), nullable=False, server_default='60.0'),
        sa.Column('force_flat_minutes_before_close', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('data_provider', sa.String(length=20), nullable=True),
        sa.Column('trading_day', sa.Date(), nullable=True),
        sa.Column('realized_pnl_today', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('trades_today', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('target_hit', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('halted', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='idle'),
        sa.Column('last_run_at', sa.DateTime(), nullable=True),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'market_type', name='uq_autopilot_user_market'),
    )
    op.create_index('ix_autopilot_config_user_id', 'autopilot_config', ['user_id'])
    op.create_index('ix_autopilot_config_enabled', 'autopilot_config', ['enabled'])

    # ---- autopilot_trades ----
    op.create_table(
        'autopilot_trades',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('config_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('market_type', sa.String(length=10), nullable=False),
        sa.Column('ticker', sa.String(length=10), nullable=False),
        sa.Column('trading_day', sa.Date(), nullable=False),
        sa.Column('entry_time', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('entry_price', sa.Float(), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('stop_price', sa.Float(), nullable=False),
        sa.Column('take_profit_price', sa.Float(), nullable=False),
        sa.Column('momentum_score', sa.Float(), nullable=True),
        sa.Column('llm_confidence', sa.Float(), nullable=True),
        sa.Column('entry_reason', sa.Text(), nullable=True),
        sa.Column('entry_order_id', sa.String(), nullable=True),
        sa.Column('status', sa.String(length=10), nullable=False, server_default='open'),
        sa.Column('exit_time', sa.DateTime(), nullable=True),
        sa.Column('exit_price', sa.Float(), nullable=True),
        sa.Column('exit_reason', sa.String(length=20), nullable=True),
        sa.Column('exit_order_id', sa.String(), nullable=True),
        sa.Column('realized_pnl', sa.Float(), nullable=True),
        sa.Column('realized_pnl_pct', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['config_id'], ['autopilot_config.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_autopilot_trades_config_id', 'autopilot_trades', ['config_id'])
    op.create_index('ix_autopilot_trades_user_id', 'autopilot_trades', ['user_id'])
    op.create_index('ix_autopilot_trades_status', 'autopilot_trades', ['status'])
    op.create_index('ix_autopilot_trades_trading_day', 'autopilot_trades', ['trading_day'])

    # ---- autopilot_daily_reports ----
    op.create_table(
        'autopilot_daily_reports',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('config_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('market_type', sa.String(length=10), nullable=False),
        sa.Column('trading_day', sa.Date(), nullable=False),
        sa.Column('capital', sa.Float(), nullable=False),
        sa.Column('daily_profit_target', sa.Float(), nullable=False),
        sa.Column('realized_pnl', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('target_met', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('return_pct', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('num_trades', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('num_winning', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('num_losing', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('win_rate', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('best_trade_pnl', sa.Float(), nullable=True),
        sa.Column('worst_trade_pnl', sa.Float(), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['config_id'], ['autopilot_config.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('config_id', 'trading_day', name='uq_autopilot_report_config_day'),
    )
    op.create_index('ix_autopilot_reports_user_id', 'autopilot_daily_reports', ['user_id'])
    op.create_index('ix_autopilot_reports_trading_day', 'autopilot_daily_reports', ['trading_day'])


def downgrade():
    op.drop_index('ix_autopilot_reports_trading_day', 'autopilot_daily_reports')
    op.drop_index('ix_autopilot_reports_user_id', 'autopilot_daily_reports')
    op.drop_table('autopilot_daily_reports')
    op.drop_index('ix_autopilot_trades_trading_day', 'autopilot_trades')
    op.drop_index('ix_autopilot_trades_status', 'autopilot_trades')
    op.drop_index('ix_autopilot_trades_user_id', 'autopilot_trades')
    op.drop_index('ix_autopilot_trades_config_id', 'autopilot_trades')
    op.drop_table('autopilot_trades')
    op.drop_index('ix_autopilot_config_enabled', 'autopilot_config')
    op.drop_index('ix_autopilot_config_user_id', 'autopilot_config')
    op.drop_table('autopilot_config')
