import sys
from os.path import abspath, dirname, join
import importlib.util

repo_root = dirname(dirname(abspath(__file__)))
sys.path.insert(0, repo_root)
# The line "from logging.config import fileConfig" has been removed.

from sqlalchemy import engine_from_config, pool

from alembic import context
from sqlmodel import SQLModel
database_module = importlib.import_module("app.database")
Base = database_module.Base

spec = importlib.util.spec_from_file_location(
    "app.config", join(repo_root, "app", "config.py")
)
config_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(config_module)
get_settings = config_module.get_settings

models_module = importlib.import_module("app.models")

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config
settings = get_settings()
database_url = settings.DATABASE_URL.replace("+aiosqlite", "").replace("+asyncpg", "")
config.set_main_option("sqlalchemy.url", database_url)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = [SQLModel.metadata, Base.metadata]

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

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
