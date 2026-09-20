from fastapi import APIRouter, Depends, HTTPException, Path
from pydantic import BaseModel

from app.core import silabo
from app.models.perfil import PerfilEstudiante
from app.services.perfil_service import PerfilService
from app.services.rag_service import RAGService, get_rag_service

router = APIRouter(prefix="/perfil", tags=["perfil"])

UserId = Path(min_length=1, max_length=100, description="Identificador del estudiante (el mismo `user_id` de /chat).")


class TemaConDificultad(BaseModel):
    tema_id: str
    tema: str
    unidad: int


class PerfilRespuesta(PerfilEstudiante):
    """El perfil tal como lo guarda el servidor más lo que la app necesita para mostrarlo."""
    es_nuevo: bool                              # aún no tiene perfil guardado: es el perfil inicial
    resumen_historial: str                      # últimos temas trabajados en una línea, el más reciente primero
    dificultades: list[TemaConDificultad]       # temas_con_dificultad con su nombre y unidad


class PuntoProgreso(BaseModel):
    fecha: str | None
    nivel: float
    motivo: str          # inicial | confusion | reflexion_correcta
    tema_id: str | None


class ProgresoUnidad(BaseModel):
    unidad: int
    titulo: str
    nivel_actual: float
    puntos: list[PuntoProgreso]


class ProgresoRespuesta(BaseModel):
    user_id: str
    unidades: list[ProgresoUnidad]


def _perfiles(rag: RAGService = Depends(get_rag_service)) -> PerfilService:
    if rag.perfiles is None:
        raise HTTPException(status_code=503, detail="El perfil del estudiante está desactivado (PERFIL_ACTIVO=false).")
    return rag.perfiles


def _respuesta(perfil: PerfilEstudiante, es_nuevo: bool) -> PerfilRespuesta:
    temas = {t.id: t for t in silabo.temas()}
    dificultades = [TemaConDificultad(tema_id=i, tema=temas[i].nombre, unidad=temas[i].unidad)
                    for i in perfil.temas_con_dificultad if i in temas]
    return PerfilRespuesta(**perfil.model_dump(), es_nuevo=es_nuevo, resumen_historial=perfil.sintesis_historial(),
                           dificultades=dificultades)


@router.get("/{user_id}", response_model=PerfilRespuesta)
def obtener_perfil(user_id: str = UserId, perfiles: PerfilService = Depends(_perfiles)):
    """Perfil del estudiante: nivel estimado por unidad (1 a 5), temas consultados y con dificultad, profundidad y
    estilo preferidos, ritmo y los últimos temas trabajados. Un estudiante sin perfil recibe el inicial (nivel 3 en
    las cuatro unidades) con `es_nuevo: true`; no se guarda hasta su primer mensaje en /chat."""
    return _respuesta(perfiles.obtener(user_id), es_nuevo=not perfiles.existe(user_id))


@router.get("/{user_id}/progreso", response_model=ProgresoRespuesta)
def obtener_progreso(user_id: str = UserId, perfiles: PerfilService = Depends(_perfiles)):
    """Evolución del nivel estimado en cada unidad: un punto inicial (nivel 3) y luego cada cambio, con su fecha,
    el motivo (`confusion` o `reflexion_correcta`) y el tema que lo provocó."""
    perfil, puntos = perfiles.obtener(user_id), perfiles.progreso(user_id)
    titulos = {u["numero"]: u["titulo"] for u in silabo.unidades()}
    return ProgresoRespuesta(user_id=user_id, unidades=[
        ProgresoUnidad(unidad=u, titulo=titulos.get(u, ""), nivel_actual=perfil.nivel(u),
                       puntos=[PuntoProgreso(**p) for p in puntos[u]])
        for u in sorted(puntos)])


@router.post("/{user_id}/reiniciar", response_model=PerfilRespuesta)
def reiniciar_perfil(user_id: str = UserId, perfiles: PerfilService = Depends(_perfiles)):
    """Borra el perfil, su progreso y sus sesiones. El estudiante vuelve a empezar desde el perfil inicial."""
    return _respuesta(perfiles.reiniciar(user_id), es_nuevo=True)
