"""003 create watchlist_items table

Revision ID: 003
Revises: 002
Create Date: 2026-01-01 00:02:00.000000

Creates the watchlist_items table for per-user stock watchlists.

Requirements: R3.1, R3.3, R3.4, R3.7, R7.4
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# ---------------------------------------------------------------------------
# Revision identifiers
# ---------------------------------------------------------------------------
revision: str = "003"
down_revision = "002"
branch_labels = None
depends_on = None


# ---------------------------------------------------------------------------
# Upgrade
# ---------------------------------------------------------------------------


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    if "watchlist_items" not in existing_tables:
        op.create_table(
            "watchlist_items",
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
                nullable=False,
            ),
            sa.Column("ticker", sa.String(), nullable=False),
            sa.Column(
                "list_name",
                sa.String(),
                nullable=False,
                server_default="Default",
            ),
            sa.Column("alert_price", sa.Numeric(18, 6), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.func.now(),
            ),
        )

        op.create_unique_constraint(
            "uq_watchlist_user_ticker_list",
            "watchlist_items",
            ["user_id", "ticker", "list_name"],
        )

        op.create_index(
            "ix_watchlist_items_user_id",
            "watchlist_items",
            ["user_id"],
        )


# ---------------------------------------------------------------------------
# Downgrade
# ---------------------------------------------------------------------------


def downgrade() -> None:
    op.drop_index("ix_watchlist_items_user_id", table_name="watchlist_items")
    op.drop_constraint(
        "uq_watchlist_user_ticker_list",
        "watchlist_items",
        type_="unique",
    )
    op.drop_table("watchlist_items")
