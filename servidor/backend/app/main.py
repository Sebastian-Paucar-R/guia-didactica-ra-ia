from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse

from app.core.config import settings
from app.api.v1.endpoints.chat import router as chat_router
from app.api.v1.endpoints.documentos import router as documentos_router

INDEX_HTML = Path(__file__).parent / "static" / "index.html"

MEDIA_TYPES = {
    ".pdf": "application/pdf",
    ".md": "text/markdown",
    ".txt": "text/plain",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    debug=settings.DEBUG
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# El RAG (get_rag_service) se instancia una sola vez al importar chat.py
app.include_router(chat_router, prefix="/api/v1")
app.include_router(documentos_router, prefix="/api/v1")


def _servir(carpeta: str, archivo: str) -> FileResponse:
    bases = {
        "originales": settings.ORIGINALES_DIR,
        "pdf": settings.PDF_DIR,
        "markdown": settings.MARKDOWN_DIR,
    }
    base = bases.get(carpeta)
    if base is not None:
        ruta = (base / archivo).resolve()
        # Sin traversal: el archivo debe estar directamente dentro de la carpeta
        if ruta.parent == base.resolve() and ruta.is_file():
            return FileResponse(
                ruta,
                media_type=MEDIA_TYPES.get(ruta.suffix.lower(), "application/octet-stream"),
                filename=ruta.name,
                content_disposition_type="inline",
            )
    raise HTTPException(status_code=404, detail=f"Documento no encontrado: {carpeta}/{archivo}")


@app.get("/documentacion/{carpeta}/{archivo}")
async def get_document_version(carpeta: str, archivo: str):
    """Sirve una copia de un documento: carpeta = originales | pdf | markdown."""
    return _servir(carpeta, archivo)


@app.get("/documentacion/{archivo}")
async def get_document(archivo: str):
    """Ruta anterior (nombre suelto): busca en pdf/, markdown/ y originales/."""
    for carpeta in ("pdf", "markdown", "originales"):
        try:
            return _servir(carpeta, archivo)
        except HTTPException:
            continue
    raise HTTPException(status_code=404, detail=f"Documento no encontrado: {archivo}")


@app.get("/", response_class=HTMLResponse)
async def root():
    return HTMLResponse(content=INDEX_HTML.read_text(encoding="utf-8"))
