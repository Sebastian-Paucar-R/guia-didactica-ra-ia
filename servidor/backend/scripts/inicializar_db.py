"""Inicializa la base de datos (DATABASE_URL) corriendo las migraciones de Alembic hasta la última versión.

Equivale a `alembic upgrade head` corrido desde `servidor/backend/`, pero sin depender de que el ejecutable
`alembic` esté en el PATH (en Windows, `pip install` a veces lo deja en una carpeta de Scripts que no lo está;
ver el aviso que imprime pip). Idempotente: si ya está al día, no hace nada.

Uso (desde servidor/backend/):
    python scripts/inicializar_db.py
"""
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config

RAIZ_BACKEND = Path(__file__).resolve().parents[1]


def inicializar() -> None:
    cfg = Config(str(RAIZ_BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(RAIZ_BACKEND / "alembic"))
    command.upgrade(cfg, "head")


if __name__ == "__main__":
    sys.path.insert(0, str(RAIZ_BACKEND))
    inicializar()
    print("Base de datos al día (alembic upgrade head).")
