import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from app.api.deps import usuario_con_consentimiento
from app.core.config import settings
from app.db.models import Usuario
from app.services.cola_service import ColaGeneracion, Espera, TiempoDeEsperaAgotado
from app.services.rag_service import get_rag_service

router = APIRouter()

# Instancia única (compartida con main.py y el router de documentos)
rag_service = get_rag_service()

# Cola de generación (ver services/cola_service.py): un módulo, una cola, para todo el proceso del servidor.
cola = ColaGeneracion(limite=settings.LIMITE_GENERACIONES_SIMULTANEAS, espera_maxima_s=settings.ESPERA_MAXIMA_COLA_S)


class ChatRequest(BaseModel):
    mensaje: str
    # Identifica la conversación: con el mismo id el tutor recuerda los turnos anteriores.
    # Si se omite, se genera uno nuevo y se devuelve para que el cliente lo reutilice.
    conversacion_id: str | None = Field(default=None, max_length=100)
    # Lección de la app Flutter en curso (ver app/core/lecciones.py): si resuelve a un tema del sílabo, la
    # recuperación de contexto se restringe a los documentos de ese tema y se salta el filtro de pertinencia
    # normal, para que una duda ambigua dentro de la lección se responda en su propio marco.
    leccion_id: str | None = Field(default=None, max_length=100)

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
    respuesta: str
    # saludo | funcionamiento | sin_documentos | respuesta | sin_contexto | redireccion | error
    tipo: str = "respuesta"
    conversacion_id: str = ""
    # True si la respuesta salió del caché semántico (sin llamar al LLM)
    desde_cache: bool = False
    # Tiempo que tardó el servidor en producir la respuesta, en milisegundos
    latencia_ms: float = 0.0
    # Nombre del tema y número de unidad del sílabo a los que pertenece la consulta; None si se redirigió, es
    # un saludo o una pregunta sobre el propio tutor
    tema_detectado: str | None = None
    unidad_detectada: int | None = None
    # Campos adicionales (no pedidos por el contrato móvil, pero sin costo para el cliente que los ignora):
    # id exacto del tema en configuracion/silabo.yaml y método con el que se decidió (palabras_clave | llm |
    # embedding | leccion | seguimiento) — los usan pruebas/evaluar_tutor.py y la auditoría de pertinencia.
    tema_id_detectado: str | None = None
    metodo_deteccion: str | None = None
    # Ajuste al perfil del estudiante con el que se generó la respuesta; None si la respuesta no se adapta
    # (saludo, redirección, "no está en los documentos"...)
    adaptacion: AjusteAplicado | None = None
    # Posición que tenía esta petición al llegar a la cola de generación (services/cola_service.py) y cuánto se
    # estimó que tardaría; ambos None si pasó directo (sin cola) o si la respuesta salió del caché.
    posicion_en_cola: int | None = None
    espera_estimada_s: float | None = None
    # Espera real medida (no la estimación al llegar); no pedido por el contrato móvil, lo usa
    # scripts/prueba_concurrencia.py para medir la cola de verdad.
    espera_real_s: float | None = None


@router.post("/chat", response_model=ChatResponse)
async def chat_with_tutor(request: ChatRequest, usuario: Usuario = Depends(usuario_con_consentimiento)):
    print(f"\n[USUARIO {usuario.uid_firebase}] → {request.mensaje}")

    conversacion_id = (request.conversacion_id or "").strip() or uuid.uuid4().hex
    try:
        result, espera = await _generar_en_cola(
            request.mensaje, conversacion_id, usuario.uid_firebase, request.leccion_id)
    except TiempoDeEsperaAgotado as e:
        raise HTTPException(status_code=503, detail=str(e))

    ubicacion = result.get("ubicacion") or {}
    return ChatResponse(
        respuesta=result.get("response", "Sin respuesta"),
        tipo=result.get("tipo", "respuesta"),
        conversacion_id=conversacion_id,
        desde_cache=result.get("desde_cache", False),
        latencia_ms=result.get("tiempo_respuesta_ms", 0.0),
        tema_detectado=ubicacion.get("tema"),
        unidad_detectada=ubicacion.get("unidad"),
        tema_id_detectado=ubicacion.get("tema_id"),
        metodo_deteccion=ubicacion.get("metodo"),
        adaptacion=result.get("adaptacion"),
        posicion_en_cola=espera.posicion_al_llegar if espera else None,
        espera_estimada_s=espera.espera_estimada_s if espera else None,
        espera_real_s=espera.espera_real_s if espera else None,
    )


async def _generar_en_cola(pregunta: str, conversation_id: str, uid: str,
                            leccion_id: str | None = None) -> tuple[dict, Espera | None]:
    """Prueba el caché primero (siempre, sin cola; se salta sola si `leccion_id` resuelve a un tema — ver
    RAGService._consultar_cache); si falla, espera un cupo de generación EN EL EVENT LOOP (`cola.turno()`,
    `asyncio.Semaphore`: no ocupa un hilo del threadpool mientras espera — ver services/cola_service.py,
    punto 1) y solo entonces despacha la generación de verdad a un hilo."""
    resultado = await run_in_threadpool(rag_service.probar_cache, pregunta, conversation_id, uid, leccion_id)
    if resultado is not None:
        return resultado, None
    async with cola.turno() as espera:
        resultado = await run_in_threadpool(rag_service.get_answer, pregunta, conversation_id, uid, leccion_id)
    return resultado, (espera if espera.ocupada else None)


@router.get("/cola/estado")
async def estado_cola():
    """Foto en vivo de la cola de generación, para que el cliente la muestre mientras espera la respuesta de un
    /chat anterior (la propia respuesta de /chat ya trae `cola` con lo que le costó a ESA petición; este
    endpoint es para sondear el estado general, sin mandar ninguna pregunta)."""
    return (await cola.estado()).como_dict()
