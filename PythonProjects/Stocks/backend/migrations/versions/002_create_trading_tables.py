"""002 create trading tables

Revision ID: 002
Revises: 001
Create Date: 2025-01-01 00:01:00.000000

Creates three tables for paper trading persistence:
  - paper_trading_accounts
  - paper_positions
  - paper_orders

Requirements: R4.1, R4.3, R7.8
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# ---------------------------------------------------------------------------
# Revision identifiers
# ---------------------------------------------------------------------------
revision: str = "002"
down_revision = "001"
branch_labels = None
depends_on = None


# ---------------------------------------------------------------------------
# Upgrade
# ---------------------------------------------------------------------------


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    # ------------------------------------------------------------------
    # paper_trading_accounts
    # ------------------------------------------------------------------
    # Guard: init_db.sql may have already created this table with a
    # different schema; skip creation if it already exists.
    if "paper_trading_accounts" not in existing_tables:
        op.create_table(
            "paper_trading_accounts",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
                nullable=False,
            ),
            sa.Column(
                "user_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                unique=True,
                nullable=False,
            ),
            sa.Column(
                "cash",
                sa.Numeric(18, 6),
                nullable=False,
                server_default="100000",
            ),
            sa.Column(
                "initial_cash",
                sa.Numeric(18, 6),
                nullable=False,
                server_default="100000",
            ),
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.Column(
                "last_updated",
                sa.DateTime(),
                nullable=False,
                server_default=sa.func.now(),
                onupdate=sa.func.now(),
            ),
        )

        op.create_index(
            "ix_paper_trading_accounts_user_id",
            "paper_trading_accounts",
            ["user_id"],
            unique=True,
        )

    # ------------------------------------------------------------------
    # paper_positions
    # ------------------------------------------------------------------
    if "paper_positions" not in existing_tables:
        op.create_table(
            "paper_positions",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
                nullable=False,
            ),
            sa.Column(
                "account_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("paper_trading_accounts.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("ticker", sa.String(), nullable=False),
            sa.Column("quantity", sa.Integer(), nullable=False),
            sa.Column("avg_entry_price", sa.Numeric(18, 6), nullable=False),
            sa.Column("current_price", sa.Numeric(18, 6), nullable=False),
            sa.Column("entry_time", sa.DateTime(), nullable=False),
            sa.Column(
                "last_updated",
                sa.DateTime(),
                nullable=False,
                server_default=sa.func.now(),
                onupdate=sa.func.now(),
            ),
        )

        op.create_index(
            "ix_paper_positions_account_id",
            "paper_positions",
            ["account_id"],
        )

    # ------------------------------------------------------------------
    # paper_orders
    # ------------------------------------------------------------------
    if "paper_orders" not in existing_tables:
        op.create_table(
            "paper_orders",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
                nullable=False,
            ),
            sa.Column(
                "account_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("paper_trading_accounts.id", ondelete="CASCADE"),
                nullable=False,
            ),
            # Domain UUID string from the in-memory Order object
            sa.Column("order_id", sa.String(), nullable=False, unique=True),
            sa.Column("ticker", sa.String(), nullable=False),
            # "buy" | "sell"
            sa.Column("side", sa.String(), nullable=False),
            # "market" | "limit" | "stop_loss" | "stop_limit"
            sa.Column("order_type", sa.String(), nullable=False),
            sa.Column("quantity", sa.Integer(), nullable=False),
            sa.Column("limit_price", sa.Numeric(18, 6), nullable=True),
            sa.Column("stop_price", sa.Numeric(18, 6), nullable=True),
            # "pending" | "filled" | "cancelled" | "rejected"
            sa.Column("status", sa.String(), nullable=False),
            sa.Column("filled_price", sa.Numeric(18, 6), nullable=True),
            sa.Column(
                "filled_quantity",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
            sa.Column(
                "commission",
                sa.Numeric(18, 6),
                nullable=False,
                server_default="0",
            ),
            sa.Column(
                "slippage",
                sa.Numeric(18, 6),
                nullable=False,
                server_default="0",
            ),
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.Column("filled_at", sa.DateTime(), nullable=True),
        )

        op.create_index(
            "ix_paper_orders_account_id",
            "paper_orders",
            ["account_id"],
        )
        op.create_index(
            "ix_paper_orders_ticker",
            "paper_orders",
            ["ticker"],
        )
        op.create_unique_constraint(
            "uq_paper_orders_order_id",
            "paper_orders",
            ["order_id"],
        )


# ---------------------------------------------------------------------------
# Downgrade
# ---------------------------------------------------------------------------


def downgrade() -> None:
    op.drop_index("ix_paper_orders_ticker", table_name="paper_orders")
    op.drop_index("ix_paper_orders_account_id", table_name="paper_orders")
    op.drop_table("paper_orders")

    op.drop_index("ix_paper_positions_account_id", table_name="paper_positions")
    op.drop_table("paper_positions")

    op.drop_index(
        "ix_paper_trading_accounts_user_id",
        table_name="paper_trading_accounts",
    )
    op.drop_table("paper_trading_accounts")
