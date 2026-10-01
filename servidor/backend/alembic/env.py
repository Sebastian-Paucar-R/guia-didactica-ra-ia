"""Configuración de Alembic: la URL real sale de app.core.config.settings.DATABASE_URL (no de alembic.ini),
así que `alembic upgrade head` respeta el mismo DATABASE_URL que usa el servidor (incluida la variable de
entorno, vía .env). target_metadata apunta a app.db.base.Base: cualquier modelo nuevo en app/db/models.py
que herede de Base entra en `alembic revision --autogenerate` sin tocar este archivo.
"""
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Import necesario para que target_metadata conozca las tablas: sin este import, models.py no se ha
# ejecutado todavía y Base.metadata estaría vacío.
from app.db import models  # noqa: F401
from app.db.base import Base
from app.core.config import settings

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Genera el SQL sin conectarse a la base (`alembic upgrade head --sql`)."""
    context.configure(
        url=settings.DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
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
