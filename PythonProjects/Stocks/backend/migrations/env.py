"""
Alembic environment configuration for StockIQ backend.

This file is executed by Alembic whenever a migration command is run.
It configures the SQLAlchemy connection and links `Base.metadata` so
that `--autogenerate` can diff ORM models against the live schema.
"""

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# Ensure the backend app root (/app) is on sys.path so that bare module
# imports like `from database import Base` resolve correctly when Alembic
# runs the env.py from inside the migrations/ subdirectory.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Import the shared DeclarativeBase so autogenerate sees all ORM models.
# Each model module must be imported BEFORE this point (or imported here)
# so its class definitions register with Base.metadata.
from database import Base  # noqa: F401

# ---------------------------------------------------------------------------
# Alembic Config object — provides access to values in alembic.ini
# ---------------------------------------------------------------------------
config = context.config

# Override the sqlalchemy.url from the DATABASE_URL environment variable.
# This means the actual connection string never lives in alembic.ini.
db_url = os.getenv(
    "DATABASE_URL",
    "postgresql://stockiq:stockiq@localhost:5432/stockiq",
)
config.set_main_option("sqlalchemy.url", db_url)

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata target for --autogenerate support.
target_metadata = Base.metadata


# ---------------------------------------------------------------------------
# Run migrations offline (no DB connection required — generates SQL script)
# ---------------------------------------------------------------------------

def run_migrations_offline() -> None:
    """
    Run migrations without a live DB connection.
    Alembic emits the SQL directly to stdout or a file, suitable for
    review before applying to production.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------------------------
# Run migrations online (with a live DB connection)
# ---------------------------------------------------------------------------

def run_migrations_online() -> None:
    """
    Run migrations against a live database connection.
    Creates the engine from config, acquires a connection, and applies
    pending migrations.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
