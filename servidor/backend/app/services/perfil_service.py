"""Persistencia del perfil del estudiante en SQLite (perfiles.db), por `user_id`.

Tres tablas: `perfiles` (el perfil completo en JSON), `progreso` (cada cambio del nivel estimado de una unidad, para
dibujar su evolución) y `sesiones` (mensajes e instantes de cada conversación, de donde sale el ritmo). Sigue el
patrón de `cache_service`: una conexión por operación, sin estado compartido entre hilos, el archivo queda libre
entre consultas y sobrevive a reinicios. Las actualizaciones (leer, cambiar, escribir) corren en una transacción
`BEGIN IMMEDIATE`, así que dos mensajes simultáneos del mismo estudiante no pisan uno el cambio del otro.

Este módulo no decide cuándo cambia un perfil: `registrar_turno` recibe la función que lo modifica
(`adaptacion_service.aplicar_turno`) y se limita a hacerlo de forma atómica y a guardar el resultado.
"""
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Callable

from app.models.perfil import UNIDADES, CambioNivel, NIVEL_INICIAL, PerfilEstudiante, Ritmo, ahora

_ESQUEMA = """
CREATE TABLE IF NOT EXISTS perfiles (
    user_id TEXT PRIMARY KEY,
    datos TEXT NOT NULL,                 -- PerfilEstudiante en JSON
    creado_en TEXT NOT NULL,
    actualizado_en TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS progreso (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    unidad INTEGER NOT NULL,
    nivel REAL NOT NULL,                 -- nivel estimado después del cambio
    motivo TEXT NOT NULL,
    tema_id TEXT,
    fecha TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_progreso_usuario ON progreso (user_id, unidad, id);
CREATE TABLE IF NOT EXISTS sesiones (
    user_id TEXT NOT NULL,
    conversation_id TEXT NOT NULL,
    mensajes INTEGER NOT NULL,
    inicio TEXT NOT NULL,
    ultimo TEXT NOT NULL,
    PRIMARY KEY (user_id, conversation_id)
);
"""

Actualizador = Callable[[PerfilEstudiante], "list[CambioNivel]"]


class PerfilService:
    def __init__(self, ruta: Path | str, reloj: Callable[[], str] = ahora):
        self.ruta = Path(ruta)
        self.reloj = reloj
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        with self._conexion() as con:
            con.executescript(_ESQUEMA)

    # ------------------------------------------------------------------ conexiones

    @contextmanager
    def _conexion(self):
        con = sqlite3.connect(self.ruta, timeout=10, isolation_level=None)   # transacciones explícitas
        try:
            yield con
        finally:
            con.close()

    @contextmanager
    def _transaccion(self):
        with self._conexion() as con:
            con.execute("BEGIN IMMEDIATE")   # toma el bloqueo de escritura ya: lectura-modificación-escritura atómica
            try:
                yield con
            except BaseException:
                con.execute("ROLLBACK")
                raise
            con.execute("COMMIT")

    @staticmethod
    def _leer(con, user_id: str) -> PerfilEstudiante | None:
        fila = con.execute("SELECT datos FROM perfiles WHERE user_id = ?", (user_id,)).fetchone()
        return PerfilEstudiante.model_validate_json(fila[0]) if fila else None

    @staticmethod
    def _guardar(con, perfil: PerfilEstudiante) -> None:
        con.execute(
            "INSERT INTO perfiles (user_id, datos, creado_en, actualizado_en) VALUES (?, ?, ?, ?) "
            "ON CONFLICT (user_id) DO UPDATE SET datos = excluded.datos, actualizado_en = excluded.actualizado_en",
            (perfil.user_id, perfil.model_dump_json(), perfil.creado_en, perfil.actualizado_en))

    # ------------------------------------------------------------------ consulta

    def existe(self, user_id: str) -> bool:
        with self._conexion() as con:
            return con.execute("SELECT 1 FROM perfiles WHERE user_id = ?", (user_id,)).fetchone() is not None

    def obtener(self, user_id: str) -> PerfilEstudiante:
        """El perfil guardado o, si el estudiante aún no tiene, uno inicial (que no se persiste hasta su primer turno)."""
        with self._conexion() as con:
            perfil = self._leer(con, user_id)
        return perfil or PerfilEstudiante(user_id=user_id)

    def progreso(self, user_id: str) -> dict[int, list[dict]]:
        """Evolución del nivel estimado por unidad: un punto inicial (nivel 3) y luego cada cambio, en orden."""
        with self._conexion() as con:
            perfil = self._leer(con, user_id)
            filas = con.execute("SELECT unidad, nivel, motivo, tema_id, fecha FROM progreso WHERE user_id = ? "
                                "ORDER BY id", (user_id,)).fetchall()
        inicio = perfil.creado_en if perfil else None
        puntos = {u: [{"fecha": inicio, "nivel": NIVEL_INICIAL, "motivo": "inicial", "tema_id": None}] for u in UNIDADES}
        for unidad, nivel, motivo, tema_id, fecha in filas:
            puntos.setdefault(unidad, []).append({"fecha": fecha, "nivel": nivel, "motivo": motivo, "tema_id": tema_id})
        return puntos

    # ------------------------------------------------------------------ escritura

    def registrar_turno(self, user_id: str, conversation_id: str | None, actualizar: Actualizador) -> PerfilEstudiante:
        """Anota el mensaje en su sesión, aplica `actualizar` al perfil (que devuelve los cambios de nivel) y lo guarda
        todo en una sola transacción. Devuelve el perfil resultante."""
        ahora_ = self.reloj()
        with self._transaccion() as con:
            perfil = self._leer(con, user_id) or PerfilEstudiante(user_id=user_id, creado_en=ahora_)
            if conversation_id:
                self._anotar_sesion(con, user_id, conversation_id, ahora_)
            cambios = actualizar(perfil) or []
            perfil.ritmo = self._ritmo(con, user_id)
            perfil.actualizado_en = ahora_
            self._guardar(con, perfil)
            con.executemany(
                "INSERT INTO progreso (user_id, unidad, nivel, motivo, tema_id, fecha) VALUES (?, ?, ?, ?, ?, ?)",
                [(user_id, c.unidad, c.nivel, c.motivo, c.tema_id, ahora_) for c in cambios])
        return perfil

    def guardar(self, perfil: PerfilEstudiante) -> None:
        """Escribe un perfil tal cual (siembra de perfiles en pruebas y evaluaciones). No toca progreso ni sesiones."""
        perfil = perfil.model_copy(update={"creado_en": perfil.creado_en or self.reloj(),
                                           "actualizado_en": self.reloj()})
        with self._transaccion() as con:
            self._guardar(con, perfil)

    def reiniciar(self, user_id: str) -> PerfilEstudiante:
        """Borra perfil, progreso y sesiones del estudiante. Devuelve el perfil inicial."""
        with self._transaccion() as con:
            for tabla in ("perfiles", "progreso", "sesiones"):
                con.execute(f"DELETE FROM {tabla} WHERE user_id = ?", (user_id,))
        return PerfilEstudiante(user_id=user_id)

    # ------------------------------------------------------------------ ritmo

    @staticmethod
    def _anotar_sesion(con, user_id: str, conversation_id: str, instante: str) -> None:
        con.execute(
            "INSERT INTO sesiones (user_id, conversation_id, mensajes, inicio, ultimo) VALUES (?, ?, 1, ?, ?) "
            "ON CONFLICT (user_id, conversation_id) DO UPDATE SET mensajes = mensajes + 1, ultimo = excluded.ultimo",
            (user_id, conversation_id, instante, instante))

    @staticmethod
    def _ritmo(con, user_id: str) -> Ritmo:
        filas = con.execute("SELECT mensajes, inicio, ultimo FROM sesiones WHERE user_id = ?", (user_id,)).fetchall()
        if not filas:
            return Ritmo()
        total = sum(m for m, _, _ in filas)
        duraciones = [(datetime.fromisoformat(u) - datetime.fromisoformat(i)).total_seconds()
                      for m, i, u in filas if m >= 2]
        return Ritmo(sesiones=len(filas), mensajes_totales=total, mensajes_por_sesion=round(total / len(filas), 2),
                     duracion_media_s=round(sum(duraciones) / len(duraciones), 1) if duraciones else 0.0)
