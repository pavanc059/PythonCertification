"""004 create real_trade_audit_log

Revision ID: 004
Revises: 003
Create Date: 2025-01-01 00:03:00.000000

Creates the immutable audit log table for real-money trade confirmation events.

Requirements: 12.1, 12.2, 12.3, 12.4, 12.5
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# ---------------------------------------------------------------------------
# Revision identifiers
# ---------------------------------------------------------------------------
revision: str = "004"
down_revision = "003"
branch_labels = None
depends_on = None


# ---------------------------------------------------------------------------
# Upgrade
# ---------------------------------------------------------------------------


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    if "real_trade_audit_log" not in existing_tables:
        op.create_table(
            "real_trade_audit_log",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
                nullable=False,
            ),
            sa.Column(
                "user_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="RESTRICT"),
                nullable=False,
            ),
            sa.Column("ticker", sa.String(10), nullable=False),
            sa.Column("side", sa.String(4), nullable=False),          # "buy"|"sell"
            sa.Column("order_type", sa.String(20), nullable=False),
            sa.Column("quantity", sa.Integer(), nullable=False),
            sa.Column("limit_price", sa.Numeric(18, 6), nullable=True),
            sa.Column("stop_price", sa.Numeric(18, 6), nullable=True),
            sa.Column("confirmation_text", sa.Text(), nullable=False),
            sa.Column("outcome", sa.String(10), nullable=False),       # "confirmed"|"rejected"|"expired"
            sa.Column("ip_address", sa.String(45), nullable=True),
            sa.Column("user_agent", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.func.now(),
            ),
        )

        op.create_index(
            "ix_rtaudit_user_created",
            "real_trade_audit_log",
            ["user_id", "created_at"],
        )

        op.create_index(
            "ix_rtaudit_ticker",
            "real_trade_audit_log",
            ["ticker"],
        )


# ---------------------------------------------------------------------------
# Downgrade
# ---------------------------------------------------------------------------


def downgrade() -> None:
    op.drop_index("ix_rtaudit_ticker", table_name="real_trade_audit_log")
    op.drop_index("ix_rtaudit_user_created", table_name="real_trade_audit_log")
    op.drop_table("real_trade_audit_log")
