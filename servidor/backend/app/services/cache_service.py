"""Caché semántico de respuestas, persistido en SQLite (cache_respuestas.db).

Una pregunta nueva se compara por similitud coseno (embedding de all-MiniLM-L6-v2, el mismo del RAG) con las
preguntas ya respondidas; si alguna llega al umbral se devuelve su respuesta sin llamar al LLM. No hay copia en
memoria: cada consulta lee SQLite, así que el caché sobrevive a reinicios y no puede quedar desincronizado.

Solo por similitud, el modelo de embeddings no separa bien "misma pregunta redactada distinto" de "otra
pregunta parecida" en español (ver documentacion/cache_semantico.md), así que un acierto exige además que las
dos preguntas coincidan en: el modo de respuesta que pediría el estudiante (TAREA/PROFUNDIZAR/PUNTUAL, por
señales explícitas, sin LLM), los números y siglas que nombran (ISO 9001 vs ISO 27001) y la negación
("qué es" vs "qué no es"). Son filtros previos en SQL; la similitud decide entre los que los pasan.

Invalidación: `invalidar()` vacía las respuestas y sube un contador de versión. Quien va a guardar una respuesta
lee la versión ANTES de generarla y `guardar()` la rechaza si cambió: así una respuesta calculada con el índice
anterior no entra al caché si el índice se modificó mientras se generaba.
"""
import json
import re
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from app.services import tutor_service as tutor
from app.services.pertinencia_service import _normalizar

# Solo se guardan respuestas del tutor basadas en los documentos. No: saludo (fijo), funcionamiento (depende del
# momento), redireccion (su redacción varía a propósito), sin_documentos ni error.
TIPOS_CACHEABLES = ("respuesta", "sin_contexto")

_SIGLA = re.compile(r"\b[A-ZÁÉÍÓÚÑ]{3,}\b")
_PARTES_NORMA = {"iso", "iec", "ieee"}
_NEGACION = re.compile(r"\b(?:no|sin|nunca|ni|tampoco|jamas)\b")

_ESQUEMA = """
CREATE TABLE IF NOT EXISTS respuestas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pregunta TEXT NOT NULL,
    embedding BLOB NOT NULL,             -- float32, normalizado (coseno = producto punto)
    intencion TEXT NOT NULL,
    huella TEXT NOT NULL,
    respuesta TEXT NOT NULL,
    contexto TEXT NOT NULL,
    fuentes TEXT NOT NULL,               -- JSON: documentos recuperados
    tipo TEXT NOT NULL,
    usos INTEGER NOT NULL DEFAULT 0,     -- reutilizaciones (0 al crearse)
    tiempo_generacion_ms REAL NOT NULL,  -- lo que costó generarla: referencia del tiempo ahorrado
    creado_en TEXT NOT NULL,
    ultimo_uso TEXT NOT NULL,
    -- ajuste al estudiante con el que se generó (perfil): '' = sin ajuste. Ver adaptacion_service.Adaptacion.segmento
    segmento TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_respuestas_clave ON respuestas (intencion, huella);
CREATE TABLE IF NOT EXISTS meta (clave TEXT PRIMARY KEY, valor);  -- contadores y datos sueltos
INSERT OR IGNORE INTO meta (clave, valor) VALUES ('version', 0);
"""


def _migrar(con) -> None:
    """Bases creadas antes del perfil del estudiante no tienen la columna `segmento`: sus entradas eran todas
    respuestas sin ajuste, que es justo lo que significa el valor por defecto ('')."""
    columnas = {fila[1] for fila in con.execute("PRAGMA table_info(respuestas)")}
    if "segmento" not in columnas:
        con.execute("ALTER TABLE respuestas ADD COLUMN segmento TEXT NOT NULL DEFAULT ''")
    con.execute("CREATE INDEX IF NOT EXISTS idx_respuestas_segmento ON respuestas (intencion, huella, segmento)")


def intencion_de(pregunta: str) -> str:
    """Modo de respuesta que la pregunta pide, sin LLM: TAREA o PROFUNDIZAR si hay señales explícitas; si no,
    PUNTUAL (incluye las ambiguas, que el flujo normal resolvería con una llamada al LLM)."""
    return tutor.detectar_intencion_por_senales(pregunta) or tutor.PUNTUAL


def huella_de(pregunta: str) -> str:
    """Lo que distingue dos preguntas casi idénticas para el modelo de embeddings: números (ISO 9001 / 27001,
    años, niveles), siglas en mayúsculas (CMMI, SPICE; ISO/IEC/IEEE no cuentan) y si hay negación."""
    numeros = sorted(set(re.findall(r"\d+", _normalizar(pregunta))))
    siglas = sorted({s.lower() for s in _SIGLA.findall(pregunta)} - _PARTES_NORMA)
    negacion = int(bool(_NEGACION.search(_normalizar(pregunta))))
    return f"n={','.join(numeros)}|s={','.join(siglas)}|neg={negacion}"


def _unitario(embedding) -> np.ndarray:
    v = np.asarray(embedding, dtype=np.float64)
    norma = np.linalg.norm(v)
    return v / norma if norma else v


def _ahora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass(frozen=True)
class Acierto:
    id: int
    pregunta: str          # la pregunta original con la que se guardó (no la que llegó ahora)
    respuesta: str
    contexto: str
    fuentes: list[str]
    tipo: str
    usos: int
    tiempo_generacion_ms: float
    similitud: float


class CacheSemantico:
    def __init__(self, ruta: Path | str, umbral: float = 0.92):
        self.ruta = Path(ruta)
        self.umbral = umbral
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        with self._conexion() as con:
            con.executescript(_ESQUEMA)
            _migrar(con)

    @contextmanager
    def _conexion(self):
        # Una conexión por operación: sin estado compartido entre hilos y el archivo queda libre entre consultas.
        con = sqlite3.connect(self.ruta, timeout=10)
        try:
            with con:  # commit al salir bien, rollback si falla
                yield con
        finally:
            con.close()

    @staticmethod
    def _sumar(con, clave: str, cantidad: float) -> None:
        con.execute("INSERT INTO meta (clave, valor) VALUES (?, ?) "
                    "ON CONFLICT (clave) DO UPDATE SET valor = valor + excluded.valor", (clave, cantidad))

    @staticmethod
    def _leer(con, clave: str, defecto=0):
        fila = con.execute("SELECT valor FROM meta WHERE clave = ?", (clave,)).fetchone()
        return defecto if fila is None else fila[0]

    # ------------------------------------------------------------------ consulta

    def version(self) -> int:
        with self._conexion() as con:
            return int(self._leer(con, "version"))

    def buscar(self, pregunta: str, embedding, segmento: str = "") -> Acierto | None:
        """Entrada más parecida con la misma intención, huella y segmento cuya similitud llegue al umbral. No
        modifica nada: el uso se anota con `registrar_acierto` (necesita el tiempo total de la respuesta).

        `segmento` es el ajuste al estudiante con el que se generaría la respuesta: una respuesta pensada para un
        nivel o una profundidad no se sirve a quien necesita otra. Solo las `sin_contexto` (no dicen nada del tema,
        solo que no está en los documentos) no se adaptan y se comparten entre todos los segmentos."""
        vector = _unitario(embedding)
        with self._conexion() as con:
            mejor_id, mejor = None, -1.0
            for id_, blob in con.execute(
                    "SELECT id, embedding FROM respuestas WHERE intencion = ? AND huella = ? "
                    "AND (segmento = ? OR (tipo = 'sin_contexto' AND segmento = ''))",
                    (intencion_de(pregunta), huella_de(pregunta), segmento)):
                candidato = np.frombuffer(blob, dtype=np.float32).astype(np.float64)
                if candidato.shape != vector.shape:      # guardada con otro modelo de embeddings
                    continue
                similitud = float(candidato @ vector)
                if similitud > mejor:
                    mejor_id, mejor = id_, similitud
            if mejor_id is None or mejor < self.umbral:
                return None
            f = con.execute("SELECT pregunta, respuesta, contexto, fuentes, tipo, usos, tiempo_generacion_ms "
                            "FROM respuestas WHERE id = ?", (mejor_id,)).fetchone()
        return Acierto(mejor_id, f[0], f[1], f[2], json.loads(f[3]), f[4], f[5], f[6], mejor)

    def registrar_acierto(self, acierto: Acierto, tiempo_respuesta_ms: float) -> None:
        """Suma un uso a la entrada (contador y fecha de último uso) y el tiempo que se ahorró: lo que costó
        generarla la primera vez menos lo que tardó en servirse desde el caché."""
        ahorrado = max(acierto.tiempo_generacion_ms - tiempo_respuesta_ms, 0.0)
        with self._conexion() as con:
            con.execute("UPDATE respuestas SET usos = usos + 1, ultimo_uso = ? WHERE id = ?",
                        (_ahora(), acierto.id))
            self._sumar(con, "aciertos", 1)
            self._sumar(con, "ms_ahorrados", ahorrado)

    def registrar_fallo(self) -> None:
        with self._conexion() as con:
            self._sumar(con, "fallos", 1)

    def registrar_omision_por_perfil(self) -> None:
        """La consulta no pasó por el caché porque su respuesta cita lo que ese estudiante ya trabajó (es personal).
        No cuenta como fallo: se lleva aparte para medir cuánto ahorro cuesta el perfil."""
        with self._conexion() as con:
            self._sumar(con, "omitidos_perfil", 1)

    # ------------------------------------------------------------------ escritura

    def guardar(self, pregunta: str, embedding, respuesta: str, contexto: str, fuentes: list[str], tipo: str,
                tiempo_generacion_ms: float, version: int, segmento: str = "") -> bool:
        """Guarda una respuesta recién generada. Devuelve False (sin guardar) si el caché se invalidó desde
        que se leyó `version`: la respuesta pudo salir de un índice ya desactualizado. `segmento` debe ser el del
        ajuste con el que realmente se generó (una `sin_contexto` va siempre sin segmento: no se adapta)."""
        ahora = _ahora()
        with self._conexion() as con:
            cursor = con.execute(
                "INSERT INTO respuestas (pregunta, embedding, intencion, huella, respuesta, contexto, fuentes, tipo, "
                "tiempo_generacion_ms, creado_en, ultimo_uso, segmento) "
                "SELECT ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ? "
                "WHERE (SELECT valor FROM meta WHERE clave = 'version') = ?",   # comprobación e inserción atómicas
                (pregunta, _unitario(embedding).astype(np.float32).tobytes(), intencion_de(pregunta),
                 huella_de(pregunta), respuesta, contexto, json.dumps(fuentes, ensure_ascii=False), tipo,
                 tiempo_generacion_ms, ahora, ahora, "" if tipo == "sin_contexto" else segmento, version))
            return cursor.rowcount == 1

    def invalidar(self, motivo: str = "") -> int:
        """Descarta TODAS las respuestas (el índice cambió y pueden estar desactualizadas). Los contadores de
        aciertos/fallos se conservan para las estadísticas. Devuelve cuántas entradas se eliminaron.

        La versión sube siempre (protege a las respuestas que se están generando ahora); el conteo de
        invalidaciones, su fecha y su motivo solo cuando realmente se descartó algo."""
        with self._conexion() as con:
            eliminadas = con.execute("DELETE FROM respuestas").rowcount
            self._sumar(con, "version", 1)
            if eliminadas:
                self._sumar(con, "invalidaciones", 1)
                con.execute("INSERT OR REPLACE INTO meta (clave, valor) VALUES ('ultima_invalidacion', ?)",
                            (_ahora(),))
                con.execute("INSERT OR REPLACE INTO meta (clave, valor) VALUES ('motivo_ultima_invalidacion', ?)",
                            (motivo,))
        return eliminadas

    # ------------------------------------------------------------------ estadísticas

    def estadisticas(self, limite: int = 10) -> dict:
        with self._conexion() as con:
            total = con.execute("SELECT COUNT(*) FROM respuestas").fetchone()[0]
            aciertos = int(self._leer(con, "aciertos"))
            fallos = int(self._leer(con, "fallos"))
            ahorrado = float(self._leer(con, "ms_ahorrados"))
            repetidas = con.execute(
                "SELECT pregunta, usos, creado_en, ultimo_uso FROM respuestas WHERE usos > 0 "
                "ORDER BY usos DESC, ultimo_uso DESC, id LIMIT ?", (limite,)).fetchall()
            invalidaciones = int(self._leer(con, "invalidaciones"))
            ultima = self._leer(con, "ultima_invalidacion", None)
            motivo = self._leer(con, "motivo_ultima_invalidacion", None)
            omitidos = int(self._leer(con, "omitidos_perfil"))
            segmentos = con.execute("SELECT segmento, COUNT(*) FROM respuestas GROUP BY segmento").fetchall()
        consultas = aciertos + fallos
        return {
            "total_entradas": total,
            "consultas": consultas,
            "aciertos": aciertos,
            "fallos": fallos,
            "tasa_aciertos": round(aciertos / consultas, 4) if consultas else 0.0,
            "preguntas_mas_repetidas": [
                {"pregunta": p, "usos": u, "creada": c, "ultimo_uso": lu} for p, u, c, lu in repetidas],
            # Estimación: por cada acierto, lo que costó generar esa respuesta la primera vez menos lo que
            # tardó en servirse desde el caché.
            "tiempo_promedio_ahorrado_ms": round(ahorrado / aciertos, 1) if aciertos else 0.0,
            "tiempo_total_ahorrado_ms": round(ahorrado, 1),
            "umbral_similitud": self.umbral,
            "invalidaciones": invalidaciones,
            "ultima_invalidacion": ultima,
            "motivo_ultima_invalidacion": motivo,
            # Coste del perfil sobre el caché: entradas por ajuste ("neutro" = sin ajuste) y consultas que no
            # pudieron usarlo porque su respuesta es personal (cita lo ya trabajado por ese estudiante)
            "entradas_por_segmento": {s or "neutro": n for s, n in segmentos},
            "omitidos_por_perfil": omitidos,
        }
