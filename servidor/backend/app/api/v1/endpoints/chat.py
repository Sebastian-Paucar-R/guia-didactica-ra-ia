import uuid

from fastapi import APIRouter
from pydantic import BaseModel, Field
from app.services.rag_service import get_rag_service

router = APIRouter()

# Instancia única (compartida con main.py y el router de documentos)
rag_service = get_rag_service()

class ChatRequest(BaseModel):
    message: str
    # Identifica al estudiante: con él el tutor adapta CÓMO explica a su perfil (ver /perfil/{user_id}). Sin él,
    # responde igual para todos.
    user_id: str | None = Field(default=None, max_length=100)
    # Identifica la conversación: con el mismo id el tutor recuerda los turnos anteriores.
    # Si se omite, se genera uno nuevo y se devuelve para que el cliente lo reutilice.
    conversation_id: str | None = Field(default=None, max_length=100)

class UbicacionSilabo(BaseModel):
    """Dónde cae la consulta en el sílabo (configuracion/silabo.yaml) y con qué método se decidió."""
    unidad: int
    tema_id: str
    tema: str
    metodo: str   # palabras_clave | llm | embedding

class ReferenciaTema(BaseModel):
    tema_id: str
    tema: str
    unidad: int

class AjusteAplicado(BaseModel):
    """Cómo se adaptó la respuesta al estudiante. `segmento` es lo que distingue una respuesta de otra en el caché."""
    nivel: str          # bajo | medio | alto (franja del estudiante en la unidad de la consulta)
    profundidad: str    # breve | media | extensa
    estilo: str         # conceptual | ejemplos | comparativo
    dificultad: bool    # el tema figura entre los que le han costado
    segmento: str       # "" = sin ajuste
    referencias: list[ReferenciaTema] = []   # temas ya trabajados en los que se apoyó la explicación

class ChatResponse(BaseModel):
    response: str
    context: str = ""
    status: str = "success"
    # saludo | funcionamiento | sin_documentos | respuesta | sin_contexto | redireccion | error
    tipo: str = "respuesta"
    conversation_id: str = ""
    # True si la respuesta salió del caché semántico (sin llamar al LLM)
    desde_cache: bool = False
    # Tiempo que tardó el servidor en producir la respuesta, en milisegundos
    tiempo_respuesta_ms: float = 0.0
    # Unidad y tema del sílabo a los que pertenece la consulta; None si se redirigió, es un saludo o una
    # pregunta sobre el propio tutor
    ubicacion: UbicacionSilabo | None = None
    # Ajuste al perfil del estudiante con el que se generó la respuesta; None si no se envió `user_id` o la
    # respuesta no se adapta (saludo, redirección, "no está en los documentos"...)
    adaptacion: AjusteAplicado | None = None

@router.post("/chat", response_model=ChatResponse)
async def chat_with_tutor(request: ChatRequest):
    print(f"\n[USUARIO] → {request.message}")

    conversation_id = (request.conversation_id or "").strip() or uuid.uuid4().hex
    result = rag_service.get_answer(request.message, conversation_id=conversation_id,
                                    user_id=(request.user_id or "").strip() or None)

    return ChatResponse(
        response=result.get("response", "Sin respuesta"),
        context=result.get("context", ""),
        status="success",
        tipo=result.get("tipo", "respuesta"),
        conversation_id=conversation_id,
        desde_cache=result.get("desde_cache", False),
        tiempo_respuesta_ms=result.get("tiempo_respuesta_ms", 0.0),
        ubicacion=result.get("ubicacion"),
        adaptacion=result.get("adaptacion"),
    )
