"""Progreso de la app (XP, racha, lecciones completadas, ejercicios resueltos): ver services/progreso_service.py
para el modelo y las reglas. Siempre el del estudiante autenticado — como /historial, ningún endpoint toma un uid
del cliente, así que no hace falta `verificar_propietario`. Alimenta además las estadísticas del docente
(GET /docente/estadisticas lee las mismas tablas).
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.api.deps import usuario_actual
from app.db.models import Usuario
from app.db.session import session_factory_por_defecto
from app.services.progreso_service import ProgresoService

router = APIRouter(prefix="/progreso", tags=["progreso"])


class ProgresoActual(BaseModel):
    xp_total: int
    racha_actual: int
    racha_mejor: int
    ultima_actividad_fecha: str | None
    lecciones_completadas: int
    ejercicios_resueltos: int
    ejercicios_correctos: int


class ResolverEjercicioRequest(BaseModel):
    correcto: bool
    leccion_id: str | None = Field(default=None, max_length=100)


def _servicio() -> ProgresoService:
    # session_factory_por_defecto() es perezoso: una sola vez por proceso, como el resto de DATABASE_URL en
    # producción. En pruebas se sustituye con app.dependency_overrides (ver tests/test_progreso.py), igual que
    # api/v1/endpoints/usuarios.py hace con get_db — nunca apuntando al singleton real.
    return ProgresoService(session_factory_por_defecto())


@router.get("/mio", response_model=ProgresoActual)
def mi_progreso(usuario: Usuario = Depends(usuario_actual), servicio: ProgresoService = Depends(_servicio)):
    datos = servicio.obtener(usuario.uid_firebase)
    return ProgresoActual(**{k: v for k, v in datos.items() if k != "uid"})


@router.post("/lecciones/{leccion_id}/completar", response_model=ProgresoActual)
def completar_leccion(leccion_id: str, usuario: Usuario = Depends(usuario_actual),
                      servicio: ProgresoService = Depends(_servicio)):
    datos = servicio.completar_leccion(usuario.uid_firebase, leccion_id)
    return ProgresoActual(**{k: v for k, v in datos.items() if k != "uid"})


@router.post("/ejercicios/{ejercicio_id}/resolver", response_model=ProgresoActual)
def resolver_ejercicio(ejercicio_id: str, cuerpo: ResolverEjercicioRequest,
                       usuario: Usuario = Depends(usuario_actual), servicio: ProgresoService = Depends(_servicio)):
    datos = servicio.resolver_ejercicio(usuario.uid_firebase, ejercicio_id, cuerpo.correcto, cuerpo.leccion_id)
    return ProgresoActual(**{k: v for k, v in datos.items() if k != "uid"})
