import uuid

from fastapi import APIRouter
from pydantic import BaseModel, Field
from app.services.rag_service import get_rag_service

router = APIRouter()

# Instancia única (compartida con main.py y el router de documentos)
rag_service = get_rag_service()

class ChatRequest(BaseModel):
    message: str
    user_id: str | None = None
    # Identifica la conversación: con el mismo id el tutor recuerda los turnos anteriores.
    # Si se omite, se genera uno nuevo y se devuelve para que el cliente lo reutilice.
    conversation_id: str | None = Field(default=None, max_length=100)

class ChatResponse(BaseModel):
    response: str
    context: str = ""
    status: str = "success"
    # saludo | funcionamiento | sin_documentos | respuesta | redireccion | error
    tipo: str = "respuesta"
    conversation_id: str = ""
    # True si la respuesta salió del caché semántico (sin llamar al LLM)
    desde_cache: bool = False
    # Tiempo que tardó el servidor en producir la respuesta, en milisegundos
    tiempo_respuesta_ms: float = 0.0

@router.post("/chat", response_model=ChatResponse)
async def chat_with_tutor(request: ChatRequest):
    print(f"\n[USUARIO] → {request.message}")

    conversation_id = (request.conversation_id or "").strip() or uuid.uuid4().hex
    result = rag_service.get_answer(request.message, conversation_id=conversation_id)

    return ChatResponse(
        response=result.get("response", "Sin respuesta"),
        context=result.get("context", ""),
        status="success",
        tipo=result.get("tipo", "respuesta"),
        conversation_id=conversation_id,
        desde_cache=result.get("desde_cache", False),
        tiempo_respuesta_ms=result.get("tiempo_respuesta_ms", 0.0),
    )
