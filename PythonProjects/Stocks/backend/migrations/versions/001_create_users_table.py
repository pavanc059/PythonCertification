"""001 create users table

Revision ID: 001
Revises:
Create Date: 2025-01-01 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# ---------------------------------------------------------------------------
# Revision identifiers (used by Alembic)
# ---------------------------------------------------------------------------
revision: str = "001"
down_revision = None
branch_labels = None
depends_on = None


# ---------------------------------------------------------------------------
# Upgrade — create the users table
# ---------------------------------------------------------------------------

def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("theme_preference", sa.String(), nullable=False, server_default="dark"),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # Unique index on email (also provides fast lookup).
    op.create_index(
        "ix_users_email",
        "users",
        ["email"],
        unique=True,
    )


# ---------------------------------------------------------------------------
# Downgrade — drop the users table
# ---------------------------------------------------------------------------

def downgrade() -> None:
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
