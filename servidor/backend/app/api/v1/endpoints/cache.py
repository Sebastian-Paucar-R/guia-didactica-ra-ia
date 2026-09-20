from fastapi import APIRouter, Depends, HTTPException

from app.services.rag_service import RAGService, get_rag_service

router = APIRouter(prefix="/cache", tags=["cache"])


@router.get("/estadisticas")
def estadisticas_cache(rag: RAGService = Depends(get_rag_service)):
    """Estadísticas del caché semántico de respuestas: total de entradas, tasa de aciertos, las diez preguntas
    más repetidas y el tiempo promedio ahorrado por acierto (estimado: lo que costó generar la respuesta la
    primera vez menos lo que tardó en servirse desde el caché)."""
    if rag.cache is None:
        raise HTTPException(status_code=503, detail="El caché semántico está desactivado (CACHE_ACTIVO=false).")
    return rag.cache.estadisticas(limite=10)
