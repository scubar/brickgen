"""Alembic environment. Database URL comes from backend.config.settings."""
import sys
from pathlib import Path

# Add project root so "backend" can be imported
_project_root = Path(__file__).resolve().parents[2]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from sqlalchemy import engine_from_config, event
from sqlalchemy import pool
from alembic import context
from backend.config import settings

# this is the Alembic Config object
config = context.config

# Set sqlalchemy.url from application config (respects DATABASE_PATH env)
db_url = f"sqlite:///{settings.database_path}"
config.set_main_option("sqlalchemy.url", db_url)

# Configure only the alembic logger so we don't override the app's root logger
# (fileConfig(alembic.ini) would set root to WARN and hide API/job INFO logs)
import logging
logging.getLogger("alembic").setLevel(logging.INFO)

# Import Base so that target_metadata is available for autogenerate
from backend.database import Base, apply_sqlite_pragmas
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    if db_url.startswith("sqlite"):
        @event.listens_for(connectable, "connect")
        def _set_sqlite_pragmas(dbapi_connection, _connection_record):
            apply_sqlite_pragmas(dbapi_connection)

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
