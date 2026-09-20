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
