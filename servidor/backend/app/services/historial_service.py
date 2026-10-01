"""Persiste cada turno del chat (pregunta del estudiante + respuesta del tutor) en `conversaciones`/`mensajes`.

Antes, la única memoria de una conversación era `memoria_service.MemoriaConversacional`, en RAM: rápida (la usa
el flujo del tutor en cada mensaje, para reformular seguimientos) pero se pierde al reiniciar el servidor y no
sirve para nada fuera del proceso. Este servicio guarda el historial de verdad, en la base de datos: lo necesita
la pantalla de historial de la app, y `mensajes` es la fuente de las estadísticas docentes (preguntas por unidad,
temas con más dificultad). Las dos cosas conviven a propósito: RAM para la latencia del turno actual, base de
datos para que el historial sobreviva y se pueda consultar.
"""
from typing import Callable

from sqlalchemy import select

from app.db.models import Conversacion, Mensaje
from app.db.session import SessionFactory
from app.models.perfil import ahora


class HistorialService:
    def __init__(self, session_factory: SessionFactory, reloj: Callable[[], str] = ahora):
        self.session_factory = session_factory
        self.reloj = reloj

    def registrar_turno(self, uid: str, conversation_id: str, pregunta: str, respuesta: str, tipo: str,
                        desde_cache: bool = False, latencia_ms: float | None = None,
                        tema_detectado: str | None = None, unidad_detectada: int | None = None) -> None:
        """Crea la conversación si es la primera vez que se ve ese `conversation_id`, y agrega los dos mensajes
        del turno (el del estudiante y el del tutor). `tema_detectado`/`unidad_detectada` son los de `ubicacion`
        (None si el turno no cayó en ningún tema del sílabo: saludo, redirección...)."""
        ahora_ = self.reloj()
        with self.session_factory() as ses:
            conv = ses.get(Conversacion, conversation_id)
            if conv is None:
                ses.add(Conversacion(id=conversation_id, uid_firebase=uid, titulo=pregunta[:200],
                                     fecha_inicio=ahora_, fecha_ultimo_mensaje=ahora_))
            else:
                conv.fecha_ultimo_mensaje = ahora_
            ses.add(Mensaje(conversacion_id=conversation_id, rol="estudiante", contenido=pregunta,
                            tema_detectado=tema_detectado, unidad_detectada=unidad_detectada, fecha=ahora_))
            ses.add(Mensaje(conversacion_id=conversation_id, rol="tutor", contenido=respuesta, tipo=tipo,
                            desde_cache=desde_cache, latencia_ms=latencia_ms, tema_detectado=tema_detectado,
                            unidad_detectada=unidad_detectada, fecha=ahora_))
            ses.commit()

    def conversaciones_de(self, uid: str) -> list[dict]:
        """Conversaciones del estudiante, más reciente primero (para la pantalla de historial de la app)."""
        with self.session_factory() as ses:
            filas = ses.execute(
                select(Conversacion).where(Conversacion.uid_firebase == uid)
                .order_by(Conversacion.fecha_ultimo_mensaje.desc())
            ).scalars().all()
            return [{"id": c.id, "titulo": c.titulo, "fecha_inicio": c.fecha_inicio,
                    "fecha_ultimo_mensaje": c.fecha_ultimo_mensaje} for c in filas]

    def mensajes_de(self, uid: str, conversation_id: str) -> list[dict] | None:
        """Mensajes de una conversación del estudiante, en orden; None si la conversación no existe o no es
        suya (un estudiante no puede leer el historial de otro)."""
        with self.session_factory() as ses:
            conv = ses.get(Conversacion, conversation_id)
            if conv is None or conv.uid_firebase != uid:
                return None
            filas = ses.execute(
                select(Mensaje).where(Mensaje.conversacion_id == conversation_id).order_by(Mensaje.id)
            ).scalars().all()
            return [{"rol": m.rol, "contenido": m.contenido, "tipo": m.tipo, "fecha": m.fecha} for m in filas]
