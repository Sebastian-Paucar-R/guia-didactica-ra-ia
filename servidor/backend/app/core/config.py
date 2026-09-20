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
