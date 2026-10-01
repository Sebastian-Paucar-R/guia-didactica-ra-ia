"""Base declarativa de SQLAlchemy: todos los modelos ORM (app/db/models.py) heredan de aquí. Separado de
models.py para que Alembic (alembic/env.py) pueda importar los metadatos sin arrastrar el resto de la app."""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
