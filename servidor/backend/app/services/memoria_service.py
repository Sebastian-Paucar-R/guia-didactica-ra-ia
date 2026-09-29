"""Memoria conversacional en RAM, por conversation_id.

Guarda los últimos turnos de cada conversación para que el tutor entienda seguimientos como
"explícame eso mejor". Es deliberadamente simple: vive en el proceso (se pierde al reiniciar el
servidor) y está acotada en turnos por conversación y en número de conversaciones (LRU) para que
no crezca sin límite.
"""
import threading
from collections import OrderedDict
from dataclasses import dataclass


@dataclass(frozen=True)
class Turno:
    pregunta: str
    respuesta: str
    tipo: str = "respuesta"
    intencion: str = ""   # PUNTUAL | PROFUNDIZAR | TAREA; vacío si no se conoce (p. ej. respuesta servida del caché)
    ubicacion: dict | None = None   # {unidad, tema_id, tema, metodo} del turno; None si no se ubicó (saludo, error...)


class MemoriaConversacional:
    def __init__(self, max_turnos: int = 8, max_conversaciones: int = 200):
        self.max_turnos = max_turnos
        self.max_conversaciones = max_conversaciones
        self._conversaciones: OrderedDict[str, list[Turno]] = OrderedDict()
        self._lock = threading.Lock()

    def obtener(self, conversation_id: str | None, ultimos: int | None = None) -> list[Turno]:
        if not conversation_id:
            return []
        with self._lock:
            turnos = list(self._conversaciones.get(conversation_id, []))
        return turnos[-ultimos:] if ultimos else turnos

    def agregar(self, conversation_id: str | None, pregunta: str, respuesta: str, tipo: str = "respuesta",
                intencion: str = "", ubicacion: dict | None = None) -> None:
        if not conversation_id:
            return
        with self._lock:
            turnos = self._conversaciones.setdefault(conversation_id, [])
            turnos.append(Turno(pregunta, respuesta, tipo, intencion, ubicacion))
            del turnos[:-self.max_turnos]
            self._conversaciones.move_to_end(conversation_id)
            while len(self._conversaciones) > self.max_conversaciones:
                self._conversaciones.popitem(last=False)

    def olvidar(self, conversation_id: str) -> None:
        with self._lock:
            self._conversaciones.pop(conversation_id, None)

    def __len__(self) -> int:
        return len(self._conversaciones)
