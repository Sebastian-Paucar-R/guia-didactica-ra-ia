from pathlib import Path

import anyio.to_thread
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse

from app.core.config import settings
from app.api.v1.endpoints.cache import router as cache_router
from app.api.v1.endpoints.chat import router as chat_router
from app.api.v1.endpoints.docente import router as docente_router
from app.api.v1.endpoints.documentos import router as documentos_router
from app.api.v1.endpoints.historial import router as historial_router
from app.api.v1.endpoints.perfil import router as perfil_router
from app.api.v1.endpoints.progreso import router as progreso_router
from app.api.v1.endpoints.salud import router as salud_router
from app.api.v1.endpoints.usuarios import router as usuarios_router

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
    # "*" con allow_credentials=True es una combinación inválida (los navegadores la rechazan: con comodín no se
    # pueden mandar credenciales). No hace falta aquí de todas formas: la identidad va en el header Authorization
    # (Bearer <id_token> de Firebase), no en cookies, así que ninguna petición de este backend depende de
    # credenciales de navegador. Orígenes abiertos sirven tanto a la página de prueba (file:// o localhost) como
    # al cliente móvil (que no manda Origin), sin la combinación insegura.
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# El RAG (get_rag_service) se instancia una sola vez al importar chat.py
app.include_router(chat_router, prefix="/api/v1")
app.include_router(documentos_router, prefix="/api/v1")
app.include_router(cache_router, prefix="/api/v1")
app.include_router(perfil_router, prefix="/api/v1")
app.include_router(usuarios_router, prefix="/api/v1")
app.include_router(historial_router, prefix="/api/v1")
app.include_router(docente_router, prefix="/api/v1")
app.include_router(progreso_router, prefix="/api/v1")
app.include_router(salud_router, prefix="/api/v1")


@app.on_event("startup")
async def _subir_limite_threadpool() -> None:
    """Defensa adicional, no la protección principal: la cola de generación (services/cola_service.py) ya evita
    que esperar un cupo consuma un hilo del threadpool (usa asyncio.Semaphore, no threading.Semaphore), así que
    en teoría el límite por defecto de anyio (40) nunca debería agotarse solo por estudiantes en cola. Pero la
    carga de documentos y el reindexado (api/v1/endpoints/documentos.py) sí son funciones síncronas largas
    despachadas al threadpool, y pueden coincidir con tráfico de chat; subir el límite da margen sin costo real
    (son hilos ociosos hasta que se usan, no procesos).
    """
    anyio.to_thread.current_default_thread_limiter().total_tokens = max(
        100, settings.LIMITE_GENERACIONES_SIMULTANEAS * 10)


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
