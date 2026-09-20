import pytest
from langchain_core.runnables import RunnableLambda
from langchain_core.embeddings import DeterministicFakeEmbedding

from app.core.config import settings
from app.services.rag_service import RAGService


@pytest.fixture(autouse=True)
def sin_cache_real(tmp_path, monkeypatch):
    """Ningún test toca el cache_respuestas.db real, y por defecto el caché está apagado para que las preguntas
    repetidas de los demás tests sigan pasando por el LLM. test_cache.py lo activa pasando su propia instancia."""
    monkeypatch.setattr(settings, "CACHE_ACTIVO", False)
    monkeypatch.setattr(settings, "CACHE_DB_PATH", tmp_path / "cache_respuestas.db")


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
