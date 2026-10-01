import pytest
from langchain_core.runnables import RunnableLambda
from langchain_core.embeddings import DeterministicFakeEmbedding

from app.core.config import settings
from app.db.base import Base
from app.db import models as db_models  # noqa: F401  (registra las tablas en Base.metadata)
from app.db.models import Usuario as UsuarioORM
from app.db.session import crear_engine, crear_sessionmaker
from app.services.rag_service import RAGService


@pytest.fixture(autouse=True)
def sin_cache_real(tmp_path, monkeypatch):
    """Ningún test toca cache_respuestas.db ni la base relacional real. El caché empieza apagado (por defecto)
    para que las preguntas repetidas de otros tests sigan pasando por el LLM; test_cache.py lo activa pasando su
    propia instancia. DATABASE_URL apunta a un SQLite nuevo por test, con el esquema ya migrado (create_all: para
    los tests basta, sin pasar por Alembic — ver backend/alembic/ para las migraciones reales)."""
    monkeypatch.setattr(settings, "CACHE_ACTIVO", False)
    monkeypatch.setattr(settings, "CACHE_DB_PATH", tmp_path / "cache_respuestas.db")
    database_url = f"sqlite:///{(tmp_path / 'tutor.db').as_posix()}"
    monkeypatch.setattr(settings, "DATABASE_URL", database_url)
    Base.metadata.create_all(crear_engine(database_url))


@pytest.fixture
def db_session_factory(tmp_path):
    """Sesiones sobre la misma base relacional de prueba que acaba de crear `sin_cache_real` (mismo DATABASE_URL:
    esta fixture no crea una base aparte, solo abre una fábrica de sesiones hacia la que ya existe)."""
    return crear_sessionmaker(database_url=settings.DATABASE_URL)


def usuario_de_prueba(uid: str = "u-test", rol: str = "estudiante", consentimiento: bool = True,
                      correo: str | None = None) -> UsuarioORM:
    """Un Usuario ORM listo para insertar o para devolver directo desde un dependency_override de
    `usuario_actual` (ver `cliente_autenticado`). No pasa por Firebase: es exactamente lo que la app guardaría
    si lo hubiera verificado."""
    return UsuarioORM(
        uid_firebase=uid, correo=correo or f"{uid}@example.com", nombre="Estudiante de prueba", foto_url=None,
        proveedor="password", rol=rol, fecha_registro="2026-01-01T00:00:00+00:00",
        ultimo_acceso="2026-01-01T00:00:00+00:00", consentimiento_aceptado=consentimiento,
        consentimiento_fecha="2026-01-01T00:00:00+00:00" if consentimiento else None)


def sembrar_usuario(session_factory, uid: str = "u-test", rol: str = "estudiante", consentimiento: bool = True) -> None:
    """Inserta el Usuario en la base de prueba (las tablas perfiles/conversaciones/eventos_perfil tienen clave
    foránea a usuarios, y SQLite la exige igual que PostgreSQL: ver app/db/session.py). Usarlo antes de sembrar un
    perfil o un turno de historial directamente (sin pasar por la app, que ya lo crea sola en el primer /chat)."""
    with session_factory() as ses:
        if ses.get(UsuarioORM, uid) is None:
            ses.add(usuario_de_prueba(uid, rol, consentimiento))
            ses.commit()


@pytest.fixture
def docs(tmp_path, monkeypatch):
    """documentacion/ temporal: los tests nunca tocan la carpeta ni la base vectorial reales."""
    raiz = tmp_path / "documentacion"
    monkeypatch.setattr(settings, "DOCUMENTACION_DIR", raiz)
    return raiz


@pytest.fixture
def rag(tmp_path, docs):
    (docs / "markdown").mkdir(parents=True)
    return RAGService(
        embeddings=DeterministicFakeEmbedding(size=32),
        persist_dir=tmp_path / "base_vectorial",
        docs_dir=docs,
        sincronizar_al_iniciar=False,
    )


def texto_largo(tema: str, parrafos: int = 12) -> str:
    """Markdown de varios chunks (el splitter corta a 1000 caracteres)."""
    return "\n\n".join(
        f"## {tema} sección {i}\n\n" + f"Contenido de {tema}, parte {i}. " * 25 for i in range(parrafos)
    )


class LLMFalso:
    """LLM de mentira (Runnable) que cuenta llamadas y guarda los prompts recibidos.

    `respuesta` puede ser un texto fijo, una excepción (se lanza) o una lista: cada llamada
    consume el primer elemento y, al quedar uno, lo repite."""

    def __init__(self, respuesta="Respuesta del LLM"):
        self.respuesta = respuesta
        self.prompts: list[str] = []

    @property
    def llamadas(self) -> int:
        return len(self.prompts)

    def llamadas_con(self, fragmento: str) -> int:
        """Llamadas cuyo prompt contiene `fragmento` (el clasificador se usa para varias tareas)."""
        return sum(fragmento in p for p in self.prompts)

    def __call__(self, valor_prompt):
        self.prompts.append(valor_prompt.to_string())
        respuesta = self.respuesta
        if isinstance(respuesta, list):
            respuesta = respuesta.pop(0) if len(respuesta) > 1 else respuesta[0]
        if isinstance(respuesta, Exception):
            raise respuesta
        return respuesta

    def runnable(self):
        return RunnableLambda(self)
