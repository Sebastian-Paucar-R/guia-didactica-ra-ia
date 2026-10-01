"""Estadísticas agregadas para el docente (Capítulo IV): nunca expone qué contestó o cómo va un estudiante en
particular (para eso está GET /perfil/{user_id}, que también exige ser ese estudiante o tener rol docente/admin).
"""
from collections import Counter
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import requiere_rol
from app.core import silabo
from app.db.models import Mensaje, Perfil, ProgresoEstudiante, Usuario
from app.db.session import get_db
from app.models.perfil import NIVEL_INICIAL

router = APIRouter(prefix="/docente", tags=["docente"])


class PreguntasPorUnidad(BaseModel):
    unidad: int
    titulo: str
    preguntas: int


class TemaConDificultad(BaseModel):
    tema_id: str
    tema: str
    unidad: int
    estudiantes: int   # cuántos perfiles lo tienen marcado como dificultad ahora mismo


class EvolucionUnidad(BaseModel):
    unidad: int
    titulo: str
    nivel_medio_actual: float
    cambio_medio: float   # nivel_medio_actual - NIVEL_INICIAL (positivo = la unidad mejora en promedio)


class ProgresoAgregado(BaseModel):
    """De progreso_estudiante (app Flutter: lecciones, ejercicios, XP, racha) — ver services/progreso_service.py.
    Es gamificación declarada por el estudiante en la app, distinta del nivel ESTIMADO de arriba."""
    estudiantes_con_progreso: int
    xp_total_acumulado: int
    lecciones_completadas_total: int
    ejercicios_resueltos_total: int
    ejercicios_correctos_total: int
    racha_actual_media: float


class EstadisticasDocente(BaseModel):
    estudiantes_totales: int
    estudiantes_activos: int
    dias_actividad_reciente: int
    preguntas_por_unidad: list[PreguntasPorUnidad]
    temas_con_mas_dificultad: list[TemaConDificultad]
    evolucion_por_unidad: list[EvolucionUnidad]
    progreso_app: ProgresoAgregado


@router.get("/estadisticas", response_model=EstadisticasDocente)
def estadisticas(dias_actividad_reciente: int = Query(7, ge=1, le=90),
                 _: Usuario = Depends(requiere_rol("docente", "admin")), db: Session = Depends(get_db)):
    """Estudiantes activos, preguntas por unidad, temas con más dificultad y cuánto se movió en promedio el nivel
    estimado por unidad frente al inicial (NIVEL_INICIAL = 3.0). Los temas y unidades salen de
    configuracion/silabo.yaml (core/silabo.py); los conteos, de `mensajes` (preguntas por unidad) y `perfiles`
    (dificultades y nivel: se leen todos los perfiles y se agregan en Python — para el tamaño de un curso esto es
    más simple y suficientemente rápido que exigirle a cada motor de base de datos el mismo SQL sobre JSON)."""
    limite_fecha = (datetime.now(timezone.utc) - timedelta(days=dias_actividad_reciente)).isoformat(timespec="seconds")

    total = db.execute(select(func.count()).select_from(Usuario).where(Usuario.rol == "estudiante")).scalar_one()
    activos = db.execute(select(func.count()).select_from(Usuario)
                         .where(Usuario.rol == "estudiante", Usuario.ultimo_acceso >= limite_fecha)).scalar_one()

    titulos = {u["numero"]: u["titulo"] for u in silabo.unidades()}
    conteos_unidad = dict(db.execute(
        select(Mensaje.unidad_detectada, func.count(Mensaje.id))
        .where(Mensaje.rol == "estudiante", Mensaje.unidad_detectada.is_not(None))
        .group_by(Mensaje.unidad_detectada)
    ).all())
    preguntas_por_unidad = [
        PreguntasPorUnidad(unidad=u, titulo=titulos.get(u, ""), preguntas=conteos_unidad.get(u, 0))
        for u in sorted(titulos)]

    temas_silabo = {t.id: t for t in silabo.temas()}
    contador_dificultad: Counter[str] = Counter()
    suma_nivel: dict[int, float] = {u: 0.0 for u in titulos}
    n_perfiles = 0
    for (datos,) in db.execute(select(Perfil.datos)):
        n_perfiles += 1
        for tema_id in datos.get("temas_con_dificultad", []):
            contador_dificultad[tema_id] += 1
        for unidad_str, nivel in (datos.get("nivel_por_unidad") or {}).items():
            unidad = int(unidad_str)
            if unidad in suma_nivel:
                suma_nivel[unidad] += float(nivel)

    temas_con_mas_dificultad = [
        TemaConDificultad(tema_id=tid, tema=temas_silabo[tid].nombre, unidad=temas_silabo[tid].unidad, estudiantes=n)
        for tid, n in contador_dificultad.most_common(10) if tid in temas_silabo]

    evolucion_por_unidad = [
        EvolucionUnidad(
            unidad=u, titulo=titulos[u],
            nivel_medio_actual=round(suma_nivel[u] / n_perfiles, 2) if n_perfiles else NIVEL_INICIAL,
            cambio_medio=round((suma_nivel[u] / n_perfiles) - NIVEL_INICIAL, 2) if n_perfiles else 0.0)
        for u in sorted(titulos)]

    filas_progreso = db.execute(select(
        func.count(), func.coalesce(func.sum(ProgresoEstudiante.xp_total), 0),
        func.coalesce(func.sum(ProgresoEstudiante.lecciones_completadas), 0),
        func.coalesce(func.sum(ProgresoEstudiante.ejercicios_resueltos), 0),
        func.coalesce(func.sum(ProgresoEstudiante.ejercicios_correctos), 0),
        func.coalesce(func.avg(ProgresoEstudiante.racha_actual), 0.0),
    )).one()
    n_progreso, xp_total, lecciones_total, ejercicios_total, correctos_total, racha_media = filas_progreso
    progreso_app = ProgresoAgregado(
        estudiantes_con_progreso=n_progreso, xp_total_acumulado=xp_total,
        lecciones_completadas_total=lecciones_total, ejercicios_resueltos_total=ejercicios_total,
        ejercicios_correctos_total=correctos_total, racha_actual_media=round(float(racha_media), 2))

    return EstadisticasDocente(
        estudiantes_totales=total, estudiantes_activos=activos, dias_actividad_reciente=dias_actividad_reciente,
        preguntas_por_unidad=preguntas_por_unidad, temas_con_mas_dificultad=temas_con_mas_dificultad,
        evolucion_por_unidad=evolucion_por_unidad, progreso_app=progreso_app)
