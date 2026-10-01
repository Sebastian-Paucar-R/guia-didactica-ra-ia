"""Motor y sesiones de SQLAlchemy. `DATABASE_URL` decide el motor real (ver core/config.py):

- Sin configurar, o `sqlite:///...`: SQLite en archivo, para desarrollo local (por defecto
  `servidor/tutor.db`) — sigue el mismo patrón que `cache_respuestas.db` y el `perfiles.db` anterior.
- `postgresql+pg8000://usuario:clave@host/basededatos`: PostgreSQL, para un despliegue real con varios
  estudiantes concurrentes. El driver es `pg8000` (puro Python) y no `psycopg2`: en esta máquina de desarrollo,
  una directiva de Control de aplicaciones de Windows bloquea el binario nativo de psycopg2 (la misma clase de
  problema que ya obligó a `core/chroma_compat.py` con grpc), y `pg8000` evita el problema de raíz al no tener
  ninguna extensión compilada. SQLAlchemy trata ambos por igual: el resto del código nunca importa `pg8000` ni
  `sqlite3` directamente.

`crear_sessionmaker` (no un sessionmaker ya construido a nivel de módulo) para que cada test y cada script pueda
apuntar a su propia base sin pisar la de otro; `get_db()` es la dependencia de FastAPI para los endpoints.
"""
from collections.abc import Generator
from typing import Callable

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

SessionFactory = Callable[[], Session]


def crear_engine(database_url: str | None = None) -> Engine:
    url = database_url or settings.DATABASE_URL
    # SQLite: una conexión por hilo (el resto del proyecto ya asume "una conexión por operación": cache_service.py,
    # el perfil_service.py anterior); con SQLAlchemy basta con permitir que la conexión cruce hilos.
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    engine = create_engine(url, connect_args=connect_args, future=True)
    if url.startswith("sqlite"):
        # SQLite no exige las claves foráneas por defecto (a diferencia de PostgreSQL, que sí): sin esto, un
        # perfil o una conversación con un uid_firebase inexistente se guardaría en desarrollo sin error y
        # recién fallaría en producción. Se activa por conexión (así lo pide SQLite, no hay un ajuste global).
        @event.listens_for(engine, "connect")
        def _activar_claves_foraneas(conexion_dbapi, _registro):
            cursor = conexion_dbapi.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
    return engine


def crear_sessionmaker(engine: Engine | None = None, database_url: str | None = None) -> SessionFactory:
    return sessionmaker(bind=engine or crear_engine(database_url), expire_on_commit=False, future=True)


# Motor y sesiones por defecto de la app (perezosos: no abren nada hasta el primer uso real, para que importar
# este módulo no cree ya un archivo tutor.db en disco, por ejemplo en un test que nunca lo necesita).
_engine: Engine | None = None
_session_factory: SessionFactory | None = None


def engine_por_defecto() -> Engine:
    global _engine
    if _engine is None:
        _engine = crear_engine()
    return _engine


def session_factory_por_defecto() -> SessionFactory:
    global _session_factory
    if _session_factory is None:
        _session_factory = crear_sessionmaker(engine_por_defecto())
    return _session_factory


def get_db() -> Generator[Session, None, None]:
    """Dependencia de FastAPI: una sesión por petición, cerrada al terminar."""
    db = session_factory_por_defecto()()
    try:
        yield db
    finally:
        db.close()
