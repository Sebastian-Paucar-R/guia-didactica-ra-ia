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
    # leccion_id (app Flutter) -> tema del sílabo a priorizar al recuperar contexto; ver core/lecciones.py
    LECCIONES_PATH: Path = SERVIDOR_DIR / "configuracion" / "lecciones.json"

    EXTENSIONES_PERMITIDAS: tuple[str, ...] = (".pdf", ".docx", ".pptx", ".txt", ".md")
    MAX_UPLOAD_MB: int = 50

    # Filtro de pertinencia temática (ver documentacion en backend/documentacion/filtro_pertinencia.md)
    FILTRO_PERTINENCIA_ACTIVO: bool = True
    # Similitud coseno (0-1) del mejor fragmento recuperado; por debajo, la pregunta es "candidata a
    # fuera de tema" y se confirma con el LLM. 0.62 sale de scripts/calibrar_umbral.py: con
    # all-MiniLM-L6-v2 sobre texto en español las preguntas fuera del temario llegan hasta 0.61 y las
    # del temario bajan hasta 0.42, así que el umbral es deliberadamente alto (el LLM arbitra la zona gris).
    UMBRAL_PERTINENCIA: float = 0.62
    # Recuperación híbrida (ver services/lexico_service.py y RAGService.recuperar): a la similitud de embeddings se
    # le suman, por Reciprocal Rank Fusion, BM25 sobre el texto y el número de norma del título del documento. Con
    # false, solo embeddings (como antes). No cambia el score que usa el filtro de pertinencia: ese sigue siendo la
    # mejor similitud densa, así que UMBRAL_PERTINENCIA mantiene su calibración. Medición: reportes/calidad_recuperacion.md.
    RECUPERACION_HIBRIDA: bool = True
    # Modelo de embeddings (id de Hugging Face o carpeta local; ver core/embeddings.py). Cambiarlo reconstruye el
    # índice al arrancar y obliga a recalibrar UMBRAL_PERTINENCIA, UMBRAL_RESPALDO y CACHE_UMBRAL_SIMILITUD.
    MODELO_EMBEDDINGS: str = "sentence-transformers/all-MiniLM-L6-v2"
    MODELO_LLM: str = "llama3.2"
    # Host de Ollama (ChatOllama usa este mismo valor por defecto); GET /api/v1/salud lo consulta para saber si
    # el LLM está disponible antes de que la app deje escribir.
    OLLAMA_BASE_URL: str = "http://localhost:11434"
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

    # Perfilado adaptativo del estudiante: con el `uid` del token de Firebase, el tutor estima el nivel por unidad,
    # la profundidad y el estilo preferidos y ajusta cómo explica. Persiste en DATABASE_URL (usuarios, perfiles,
    # conversaciones, mensajes, eventos_perfil: ver app/db/models.py), aparte del caché semántico (CACHE_DB_PATH
    # arriba), que se vacía al cambiar el índice y no debe arrastrar datos de estudiantes.
    PERFIL_ACTIVO: bool = True

    # Base de datos relacional (identidad, perfiles, conversaciones/mensajes, eventos_perfil). Por defecto SQLite
    # en archivo, para desarrollo local sin nada que instalar; en un despliegue real, PostgreSQL
    # (postgresql+pg8000://usuario:clave@host/basededatos — pg8000 es puro Python, ver app/db/session.py).
    # Migraciones con Alembic (backend/alembic/): `alembic upgrade head` antes de arrancar el servidor.
    DATABASE_URL: str = f"sqlite:///{(SERVIDOR_DIR / 'tutor.db').as_posix()}"

    # Firebase Authentication: identidad del estudiante/docente (nunca se guarda una contraseña en este proyecto).
    # FIREBASE_CREDENTIALS_PATH apunta al JSON de la cuenta de servicio (descargado desde la consola de Firebase,
    # Configuración del proyecto > Cuentas de servicio); nunca se versiona (ver .gitignore). Sin él configurado,
    # la app arranca igual (no lo necesita para nada más), pero cualquier endpoint protegido falla con un 500
    # claro en vez de uno críptico de la SDK.
    FIREBASE_CREDENTIALS_PATH: Path | None = None

    # Cola de generación: cuántas respuestas del LLM pueden generarse en paralelo (ver services/cola_service.py).
    # Con más de este número de peticiones a la vez, las siguientes esperan turno; la respuesta final incluye
    # cuánto tuvieron que esperar, y GET /api/v1/cola/estado da una foto en vivo para que el cliente la muestre
    # mientras espera. 2 por defecto: con un solo LLM local (Ollama, sin cola propia) más que eso satura la GPU/CPU
    # y solo alarga la cola sin acortar el tiempo total (ver reportes/prueba_concurrencia.md).
    LIMITE_GENERACIONES_SIMULTANEAS: int = 2
    # Cuánto puede esperar una petición un cupo de generación antes de que el servidor le responda con un error
    # claro en vez de dejarla colgada indefinidamente (ver services/cola_service.py).
    ESPERA_MAXIMA_COLA_S: float = 120.0

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
