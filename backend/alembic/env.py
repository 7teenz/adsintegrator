import sys
import os
from logging.config import fileConfig

# Ensure the backend/ directory is on the path so `app` is importable.
# Inside Docker WORKDIR=/app so __file__ is /app/alembic/env.py → parent is /app.
# Running locally from backend/ folder → parent of alembic/ is also backend/.
# Both cases resolve correctly with dirname(dirname(abspath(__file__))).
_here = os.path.dirname(os.path.abspath(__file__))          # .../alembic/
_root = os.path.dirname(_here)                               # .../backend/ or /app
if _root not in sys.path:
    sys.path.insert(0, _root)

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.config import get_settings
from app.database import Base
from app import models  # noqa: F401

config = context.config
settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
