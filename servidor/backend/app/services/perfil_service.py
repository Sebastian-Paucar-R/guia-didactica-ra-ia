"""Persistencia del perfil del estudiante en la base relacional (DATABASE_URL: SQLite en desarrollo, PostgreSQL en
un despliegue real — ver app/db/session.py), por `uid` de Firebase.

Tabla `perfiles` (el perfil completo en JSON, con clave foránea a `usuarios`: ver app/db/models.py) y
`eventos_perfil` (cada cambio del nivel estimado de una unidad, para dibujar su evolución). El ritmo (mensajes por
sesión, duración media) ya no se cuenta aparte: se calcula de `conversaciones`/`mensajes`, que
`services/historial_service.py` llena con cada turno real — una sola fuente de verdad para "cuánto ha
conversado" en vez de duplicarla aquí.

Este módulo no decide cuándo cambia un perfil: `registrar_turno` recibe la función que lo modifica
(`adaptacion_service.aplicar_turno`) y se limita a hacerlo de forma atómica y a guardarlo.
"""
from datetime import datetime
from typing import Callable

from sqlalchemy import func, select

from app.db.models import Conversacion, EventoPerfil, Mensaje
from app.db.models import Perfil as PerfilORM
from app.db.session import SessionFactory
from app.models.perfil import UNIDADES, CambioNivel, NIVEL_INICIAL, PerfilEstudiante, Ritmo, ahora

Actualizador = Callable[[PerfilEstudiante], "list[CambioNivel]"]


def _a_perfil(fila: PerfilORM) -> PerfilEstudiante:
    return PerfilEstudiante.model_validate(fila.datos)


class PerfilService:
    def __init__(self, session_factory: SessionFactory, reloj: Callable[[], str] = ahora):
        self.session_factory = session_factory
        self.reloj = reloj

    # ------------------------------------------------------------------ consulta

    def existe(self, uid: str) -> bool:
        with self.session_factory() as ses:
            return ses.get(PerfilORM, uid) is not None

    def obtener(self, uid: str) -> PerfilEstudiante:
        """El perfil guardado o, si el estudiante aún no tiene, uno inicial (que no se persiste hasta su primer
        turno)."""
        with self.session_factory() as ses:
            fila = ses.get(PerfilORM, uid)
        return _a_perfil(fila) if fila else PerfilEstudiante(user_id=uid)

    def progreso(self, uid: str) -> dict[int, list[dict]]:
        """Evolución del nivel estimado por unidad: un punto inicial (nivel 3) y luego cada cambio, en orden."""
        with self.session_factory() as ses:
            perfil_fila = ses.get(PerfilORM, uid)
            eventos = ses.execute(
                select(EventoPerfil).where(EventoPerfil.uid_firebase == uid).order_by(EventoPerfil.id)
            ).scalars().all()
        inicio = perfil_fila.creado_en if perfil_fila else None
        puntos = {u: [{"fecha": inicio, "nivel": NIVEL_INICIAL, "motivo": "inicial", "tema_id": None}] for u in UNIDADES}
        for e in eventos:
            puntos.setdefault(e.unidad, []).append(
                {"fecha": e.fecha, "nivel": e.nivel, "motivo": e.motivo, "tema_id": e.tema_id})
        return puntos

    # ------------------------------------------------------------------ escritura

    def registrar_turno(self, uid: str, conversation_id: str | None, actualizar: Actualizador) -> PerfilEstudiante:
        """Aplica `actualizar` al perfil (que devuelve los cambios de nivel) y lo guarda junto con sus eventos, en
        una sola transacción. `conversation_id` ya no se usa para contar sesiones aquí (ver `_ritmo`: se calcula de
        `conversaciones`/`mensajes`, que llena `historial_service`, y debe correr antes que esto en el mismo turno
        para que el ritmo cuente el mensaje actual); se conserva en la firma porque es información del turno, por
        si una futura señal la necesita. Devuelve el perfil resultante."""
        ahora_ = self.reloj()
        with self.session_factory() as ses:
            fila = ses.get(PerfilORM, uid)
            perfil = _a_perfil(fila) if fila else PerfilEstudiante(user_id=uid, creado_en=ahora_)
            cambios = actualizar(perfil) or []
            perfil.ritmo = self._ritmo(ses, uid)
            perfil.actualizado_en = ahora_
            self._guardar(ses, perfil)
            ses.add_all(EventoPerfil(uid_firebase=uid, unidad=c.unidad, nivel=c.nivel, motivo=c.motivo,
                                     tema_id=c.tema_id, fecha=ahora_) for c in cambios)
            ses.commit()
        return perfil

    def guardar(self, perfil: PerfilEstudiante) -> None:
        """Escribe un perfil tal cual (siembra de perfiles en pruebas y evaluaciones). No toca eventos_perfil."""
        perfil = perfil.model_copy(update={"creado_en": perfil.creado_en or self.reloj(),
                                           "actualizado_en": self.reloj()})
        with self.session_factory() as ses:
            self._guardar(ses, perfil)
            ses.commit()

    def reiniciar(self, uid: str) -> PerfilEstudiante:
        """Borra perfil y eventos_perfil del estudiante (no su historial de conversaciones/mensajes: ese es un
        registro de lo que pasó, no una opinión sobre su nivel). Devuelve el perfil inicial."""
        with self.session_factory() as ses:
            fila = ses.get(PerfilORM, uid)
            if fila:
                ses.delete(fila)
            ses.query(EventoPerfil).filter(EventoPerfil.uid_firebase == uid).delete()
            ses.commit()
        return PerfilEstudiante(user_id=uid)

    @staticmethod
    def _guardar(ses, perfil: PerfilEstudiante) -> None:
        fila = ses.get(PerfilORM, perfil.user_id)
        datos = perfil.model_dump(mode="json")
        if fila is None:
            ses.add(PerfilORM(uid_firebase=perfil.user_id, datos=datos, creado_en=perfil.creado_en,
                              actualizado_en=perfil.actualizado_en))
        else:
            fila.datos = datos
            fila.actualizado_en = perfil.actualizado_en

    # ------------------------------------------------------------------ ritmo

    @staticmethod
    def _ritmo(ses, uid: str) -> Ritmo:
        """De `conversaciones`/`mensajes` (las llena `historial_service` con cada turno real): cuántas
        conversaciones tiene el estudiante, mensajes por conversación en promedio y duración media de las que
        tienen al menos dos mensajes del estudiante (con uno solo la duración no significa nada)."""
        conversaciones = ses.execute(select(Conversacion).where(Conversacion.uid_firebase == uid)).scalars().all()
        if not conversaciones:
            return Ritmo()
        conteos_por_conv = dict(ses.execute(
            select(Mensaje.conversacion_id, func.count(Mensaje.id))
            .where(Mensaje.conversacion_id.in_([c.id for c in conversaciones]), Mensaje.rol == "estudiante")
            .group_by(Mensaje.conversacion_id)
        ).all())
        duraciones = [
            (datetime.fromisoformat(c.fecha_ultimo_mensaje) - datetime.fromisoformat(c.fecha_inicio)).total_seconds()
            for c in conversaciones if conteos_por_conv.get(c.id, 0) >= 2
        ]
        total = sum(conteos_por_conv.values())
        return Ritmo(sesiones=len(conversaciones), mensajes_totales=total,
                     mensajes_por_sesion=round(total / len(conversaciones), 2),
                     duracion_media_s=round(sum(duraciones) / len(duraciones), 1) if duraciones else 0.0)
