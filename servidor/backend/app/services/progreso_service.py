"""Progreso de la app (gamificación): lecciones completadas, ejercicios resueltos, XP y racha de días
consecutivos con actividad. Distinto del perfil adaptativo (`models/perfil.py`, `services/perfil_service.py`),
que es el nivel ESTIMADO por el tutor a partir del comportamiento en el chat: esto es lo que el estudiante hizo
EN LA APP (marcó una lección como vista, resolvió un ejercicio), explícito y declarado por la app, no inferido.

Antes de este servicio, la app Flutter guardaba XP y racha solo en memoria (se perdían al cerrarla); ahora viven
en `progreso_estudiante` (un acumulado, una fila por estudiante — rápido de leer) y `eventos_progreso` (el
detalle de cada evento, para auditoría y para las estadísticas docentes).
"""
from datetime import date, datetime, timezone

from app.db.models import EventoProgreso, ProgresoEstudiante
from app.db.session import SessionFactory

# Puntos otorgados por evento. Una tabla de constantes simple: si en algún momento se necesita que varíen por
# dificultad de la lección o del ejercicio, este es el único lugar que cambiar.
XP_LECCION_COMPLETADA = 20
XP_EJERCICIO_CORRECTO = 10
XP_EJERCICIO_INCORRECTO = 2   # participación: menos que acertar, pero no cero (desalienta no intentarlo)


def _ahora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _hoy() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _dias_entre(antes: str, despues: str) -> int:
    return (date.fromisoformat(despues) - date.fromisoformat(antes)).days


class ProgresoService:
    def __init__(self, session_factory: SessionFactory):
        self.session_factory = session_factory

    # ------------------------------------------------------------------ consulta

    def obtener(self, uid: str) -> dict:
        with self.session_factory() as ses:
            fila = ses.get(ProgresoEstudiante, uid)
            return self._como_dict(fila) if fila else self._inicial(uid)

    @staticmethod
    def _inicial(uid: str) -> dict:
        return {"uid": uid, "xp_total": 0, "racha_actual": 0, "racha_mejor": 0, "ultima_actividad_fecha": None,
                "lecciones_completadas": 0, "ejercicios_resueltos": 0, "ejercicios_correctos": 0}

    @staticmethod
    def _como_dict(fila: ProgresoEstudiante) -> dict:
        return {"uid": fila.uid_firebase, "xp_total": fila.xp_total, "racha_actual": fila.racha_actual,
                "racha_mejor": fila.racha_mejor, "ultima_actividad_fecha": fila.ultima_actividad_fecha,
                "lecciones_completadas": fila.lecciones_completadas,
                "ejercicios_resueltos": fila.ejercicios_resueltos, "ejercicios_correctos": fila.ejercicios_correctos}

    # ------------------------------------------------------------------ escritura

    @staticmethod
    def _fila(ses, uid: str) -> ProgresoEstudiante:
        fila = ses.get(ProgresoEstudiante, uid)
        if fila is None:
            # Los `default=0` de las columnas solo se aplican al hacer INSERT (flush/commit): recién construido,
            # en Python el atributo sigue siendo None, y el `+=` de más abajo fallaría contra NoneType.
            fila = ProgresoEstudiante(uid_firebase=uid, xp_total=0, racha_actual=0, racha_mejor=0,
                                      lecciones_completadas=0, ejercicios_resueltos=0, ejercicios_correctos=0,
                                      actualizado_en=_ahora())
            ses.add(fila)
        return fila

    @staticmethod
    def _actualizar_racha(fila: ProgresoEstudiante) -> None:
        """Un día de actividad consecutivo al anterior suma 1; el mismo día no cambia nada (no se puede subir la
        racha dos veces el mismo día completando varias lecciones); un hueco de más de un día la reinicia a 1.
        Se guarda solo la FECHA (no la hora): la racha es por día, no por sesión."""
        hoy = _hoy()
        if fila.ultima_actividad_fecha == hoy:
            return
        if fila.ultima_actividad_fecha and _dias_entre(fila.ultima_actividad_fecha, hoy) == 1:
            fila.racha_actual += 1
        else:
            fila.racha_actual = 1
        fila.racha_mejor = max(fila.racha_mejor, fila.racha_actual)
        fila.ultima_actividad_fecha = hoy

    def completar_leccion(self, uid: str, leccion_id: str) -> dict:
        with self.session_factory() as ses:
            fila = self._fila(ses, uid)
            fila.lecciones_completadas += 1
            fila.xp_total += XP_LECCION_COMPLETADA
            self._actualizar_racha(fila)
            fila.actualizado_en = _ahora()
            ses.add(EventoProgreso(uid_firebase=uid, tipo="leccion_completada", leccion_id=leccion_id,
                                   xp_otorgado=XP_LECCION_COMPLETADA, fecha=fila.actualizado_en))
            ses.commit()
            return self._como_dict(fila)

    def resolver_ejercicio(self, uid: str, ejercicio_id: str, correcto: bool,
                           leccion_id: str | None = None) -> dict:
        xp = XP_EJERCICIO_CORRECTO if correcto else XP_EJERCICIO_INCORRECTO
        with self.session_factory() as ses:
            fila = self._fila(ses, uid)
            fila.ejercicios_resueltos += 1
            if correcto:
                fila.ejercicios_correctos += 1
            fila.xp_total += xp
            self._actualizar_racha(fila)
            fila.actualizado_en = _ahora()
            ses.add(EventoProgreso(uid_firebase=uid, tipo="ejercicio_resuelto", leccion_id=leccion_id,
                                   ejercicio_id=ejercicio_id, correcto=correcto, xp_otorgado=xp,
                                   fecha=fila.actualizado_en))
            ses.commit()
            return self._como_dict(fila)
