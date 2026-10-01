"""GET /api/v1/salud: endpoint público (sin autenticación) para que la app Flutter muestre si el backend está
disponible antes de dejar escribir al estudiante. Deliberadamente barato: no genera nada con el LLM, solo
pregunta a Ollama si está vivo (`/api/tags`, el listado de modelos, con un timeout corto) y lee contadores que ya
tiene el RAG en memoria."""
import urllib.error
import urllib.request

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.config import settings
from app.services.rag_service import RAGService, get_rag_service

router = APIRouter(tags=["salud"])

TIMEOUT_OLLAMA_S = 2.0


class EstadoSalud(BaseModel):
    estado: str              # ok | degradado (servidor arriba pero Ollama no responde)
    modelo: str
    ollama_disponible: bool
    documentos_indexados: int
    chunks_indexados: int


def _ollama_responde() -> bool:
    try:
        with urllib.request.urlopen(f"{settings.OLLAMA_BASE_URL}/api/tags", timeout=TIMEOUT_OLLAMA_S):
            return True
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


@router.get("/salud", response_model=EstadoSalud)
def salud(rag: RAGService = Depends(get_rag_service)):
    ollama_disponible = _ollama_responde()
    return EstadoSalud(
        estado="ok" if ollama_disponible else "degradado",
        modelo=settings.MODELO_LLM,
        ollama_disponible=ollama_disponible,
        documentos_indexados=len(rag.resumen_indice()["documentos"]),
        chunks_indexados=rag.contar_chunks(),
    )
