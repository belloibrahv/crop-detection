import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool, create_engine
from alembic import context

from app import create_app, db

config = context.config

DB_URI = os.getenv('DATABASE_URL', 'sqlite:///dev.db').replace('postgres://', 'postgresql://')
config.set_main_option('sqlalchemy.url', DB_URI)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

flask_app = create_app()
target_metadata = db.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option('sqlalchemy.url') or DB_URI
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={'paramstyle': 'named'},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    # Build engine DIRECTLY from the resolved DB_URI.
    # Using get_section() + set_main_option() is unreliable across
    # alembic versions; constructing the engine directly guarantees
    # the env-var override is used, not whatever stale value lives in
    # alembic.ini. This is also critical on Render where SQLite fallback
    # must be exactly the same file path in alembic, create_app() and seed.py.
    connectable = create_engine(DB_URI, poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
