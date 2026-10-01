from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import usuario_actual
from app.db.models import Usuario
from app.services.historial_service import HistorialService
from app.services.rag_service import RAGService, get_rag_service
from pydantic import BaseModel

router = APIRouter(prefix="/historial", tags=["historial"])


class ConversacionResumen(BaseModel):
    id: str
    titulo: str | None
    fecha_inicio: str
    fecha_ultimo_mensaje: str


class MensajeHistorial(BaseModel):
    rol: str
    contenido: str
    tipo: str | None
    fecha: str


def _historial(rag: RAGService = Depends(get_rag_service)) -> HistorialService:
    if rag.historial is None:
        raise HTTPException(status_code=503, detail="El historial de conversaciones no está disponible.")
    return rag.historial


@router.get("/conversaciones", response_model=list[ConversacionResumen])
def mis_conversaciones(usuario: Usuario = Depends(usuario_actual), historial: HistorialService = Depends(_historial)):
    """Las conversaciones del estudiante autenticado, más reciente primero. Siempre las suyas: no toma ningún
    id de estudiante del cliente, así que no hay nada que verificar (a diferencia de /perfil/{user_id})."""
    return [ConversacionResumen(**c) for c in historial.conversaciones_de(usuario.uid_firebase)]


@router.get("/conversaciones/{conversation_id}/mensajes", response_model=list[MensajeHistorial])
def mensajes_de_conversacion(conversation_id: str, usuario: Usuario = Depends(usuario_actual),
                             historial: HistorialService = Depends(_historial)):
    """Los mensajes de una conversación. 404 si no existe o no es del estudiante autenticado (no se distingue
    "no existe" de "es de otro": lo segundo no debe poder confirmarse tanteando ids)."""
    mensajes = historial.mensajes_de(usuario.uid_firebase, conversation_id)
    if mensajes is None:
        raise HTTPException(status_code=404, detail="Conversación no encontrada.")
    return [MensajeHistorial(**m) for m in mensajes]
