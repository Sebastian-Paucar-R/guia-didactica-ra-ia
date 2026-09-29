from pathlib import Path

from pydantic_settings import BaseSettings

# backend/app/core/config.py -> parents[3] es la carpeta servidor/
SERVIDOR_DIR = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    APP_NAME: str = "Tutor IA - Guía Didáctica RA"
    VERSION: str = "0.1.0"
    DEBUG: bool = True

    # Rutas (sobrescribibles por variable de entorno, p. ej. en tests)
    DOCUMENTACION_DIR: Path = SERVIDOR_DIR / "documentacion"
    BASE_VECTORIAL_DIR: Path = SERVIDOR_DIR / "base_vectorial"

    # Temario de la asignatura: única fuente para el filtro de pertinencia, las redirecciones y la auditoría
    SILABO_PATH: Path = SERVIDOR_DIR / "configuracion" / "silabo.yaml"

    EXTENSIONES_PERMITIDAS: tuple[str, ...] = (".pdf", ".docx", ".pptx", ".txt", ".md")
    MAX_UPLOAD_MB: int = 50

    # Filtro de pertinencia temática (ver documentacion en backend/documentacion/filtro_pertinencia.md)
    FILTRO_PERTINENCIA_ACTIVO: bool = True
    # Similitud coseno (0-1) del mejor fragmento recuperado; por debajo, la pregunta es "candidata a
    # fuera de tema" y se confirma con el LLM. 0.62 sale de scripts/calibrar_umbral.py: con
    # all-MiniLM-L6-v2 sobre texto en español las preguntas fuera del temario llegan hasta 0.61 y las
    # del temario bajan hasta 0.42, así que el umbral es deliberadamente alto (el LLM arbitra la zona gris).
    UMBRAL_PERTINENCIA: float = 0.62
    MODELO_LLM: str = "llama3.2"
    # Modelo para las llamadas cortas y deterministas (clasificar pertinencia e intención, reformular un
    # seguimiento): por defecto el mismo MODELO_LLM. Ver reportes/comparativa_modelos.md: llama3.2 clasifica bien
    # y rápido, así que separar este modelo del de generación permite la opción híbrida (clasificador pequeño +
    # generador mayor) sin recargar dos veces un modelo grande en memoria para tareas de una sola palabra.
    MODELO_CLASIFICADOR: str | None = None
    # Respuesta del tutor: tope de tokens y penalización de repeticiones (sin ellos llama3.2 llegó a generar
    # 3800 palabras en bucle) y umbral de similitud por debajo del cual el contexto se considera débil
    MAX_TOKENS_RESPUESTA: int = 1024
    REPEAT_PENALTY: float = 1.15
    UMBRAL_RESPALDO: float = 0.55
    # Ventana de contexto pedida a Ollama (su valor por defecto, 2048, truncaría el prompt del tutor)
    NUM_CTX: int = 8192

    # Memoria conversacional (en RAM, por conversation_id)
    MEMORIA_MAX_TURNOS: int = 8            # turnos guardados por conversación
    MEMORIA_TURNOS_PROMPT: int = 4         # turnos previos que se muestran al LLM
    MEMORIA_MAX_CONVERSACIONES: int = 200  # conversaciones simultáneas (LRU)

    # Caché semántico de respuestas (SQLite persistente; ver services/cache_service.py). La respuesta guardada
    # se reutiliza si la similitud coseno de la pregunta con la guardada llega a CACHE_UMBRAL_SIMILITUD.
    # Calibrado con scripts/calibrar_cache.py (embeddings reales; detalle en documentacion/cache_semantico.md):
    # con all-MiniLM-L6-v2 en español la misma pregunta con cambios de forma da >= 0.96, las reformulaciones
    # de fondo 0.53-0.90 (no acertarán), y ya hay preguntas DISTINTAS en 0.927 ("qué es X" / "cuáles son las
    # características de X"). Con 0.92 se serviría la respuesta equivocada; 0.95 no pierde ningún acierto de la
    # muestra. Bajarlo da más aciertos a costa de más respuestas de otra pregunta.
    CACHE_ACTIVO: bool = True
    CACHE_UMBRAL_SIMILITUD: float = 0.95
    CACHE_DB_PATH: Path = SERVIDOR_DIR / "cache_respuestas.db"

    # Perfilado adaptativo del estudiante (SQLite persistente; ver services/perfil_service.py). Con `user_id` en
    # /chat el tutor estima el nivel por unidad, la profundidad y el estilo preferidos y ajusta cómo explica. Base
    # aparte del caché: el caché se vacía al cambiar el índice y los perfiles no deben perderse.
    PERFIL_ACTIVO: bool = True
    PERFIL_DB_PATH: Path = SERVIDOR_DIR / "perfiles.db"

    class Config:
        env_file = ".env"

    @property
    def BASE_DIR(self) -> Path:
        """Carpeta servidor/; las rutas que se devuelven por la API son relativas a ella."""
        return SERVIDOR_DIR

    @property
    def ORIGINALES_DIR(self) -> Path:
        return self.DOCUMENTACION_DIR / "originales"

    @property
    def PDF_DIR(self) -> Path:
        return self.DOCUMENTACION_DIR / "pdf"

    @property
    def MARKDOWN_DIR(self) -> Path:
        return self.DOCUMENTACION_DIR / "markdown"


settings = Settings()
