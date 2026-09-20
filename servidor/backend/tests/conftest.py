import pytest
from langchain_core.embeddings import DeterministicFakeEmbedding

from app.core.config import settings
from app.services.rag_service import RAGService


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
