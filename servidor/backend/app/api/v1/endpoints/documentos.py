import glob
import os
import re
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel

from app.api.deps import requiere_rol
from app.core.config import settings
from app.db.models import Usuario
from app.services.conversion_service import ConversionError, convertir
from app.services.rag_service import ESTADO_ERROR, RAGService, get_rag_service

router = APIRouter(prefix="/documentos", tags=["documentos"])

_RESERVADOS_WINDOWS = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)),
                       *(f"LPT{i}" for i in range(1, 10))}


class ErrorArchivo(Exception):
    """Archivo rechazado por una regla de validación (no es un fallo interno)."""


class Rutas(BaseModel):
    original: str | None = None
    pdf: str | None = None
    markdown: str | None = None


class ResultadoArchivo(BaseModel):
    nombre: str
    rutas: Rutas
    chunks_indexados: int = 0
    estado: str  # indexado | omitido_sin_cambios | error
    detalle: str | None = None


class ResumenLote(BaseModel):
    total: int
    indexados: int
    omitidos_sin_cambios: int
    errores: int


class RespuestaSubida(BaseModel):
    resultados: list[ResultadoArchivo]
    resumen: ResumenLote


def _nombre_seguro(nombre: str | None) -> str:
    """Nombre de archivo sin carpetas ni caracteres inválidos en Windows."""
    base = Path((nombre or "").replace("\\", "/")).name.strip().strip(". ")
    base = re.sub(r'[<>:"|?*\x00-\x1f]', "_", base)
    if Path(base).stem.upper() in _RESERVADOS_WINDOWS:
        base = f"_{base}"
    return base


def _relativa(ruta: Path) -> str:
    """Ruta relativa a servidor/ (p. ej. documentacion/pdf/x.pdf), estable entre equipos."""
    try:
        return ruta.relative_to(settings.DOCUMENTACION_DIR.parent).as_posix()
    except ValueError:
        return ruta.as_posix()


def _recibir_en(carpeta: Path, archivo: UploadFile, nombre: str) -> Path:
    """Escribe el upload en `carpeta/nombre` validando tamaño (máximo y no vacío)."""
    destino = carpeta / nombre
    limite = settings.MAX_UPLOAD_MB * 1024 * 1024
    escrito = 0
    with open(destino, "wb") as salida:
        while bloque := archivo.file.read(1024 * 1024):
            escrito += len(bloque)
            if escrito > limite:
                raise ErrorArchivo(f"el archivo supera el máximo de {settings.MAX_UPLOAD_MB} MB")
            salida.write(bloque)
    if escrito == 0:
        raise ErrorArchivo("el archivo está vacío")
    return destino


def _procesar_archivo(archivo: UploadFile, rag: RAGService) -> ResultadoArchivo:
    """Guarda, convierte e indexa un archivo. Nunca lanza: los fallos se reportan en el resultado."""
    rutas = Rutas()
    nombre = archivo.filename or "(sin nombre)"
    try:
        seguro = _nombre_seguro(archivo.filename)
        if not seguro or not Path(seguro).stem:
            raise ErrorArchivo("nombre de archivo inválido")
        extension = Path(seguro).suffix.lower()
        if extension not in settings.EXTENSIONES_PERMITIDAS:
            raise ErrorArchivo(
                f"extensión no soportada ({extension or 'sin extensión'}); "
                f"permitidas: {', '.join(settings.EXTENSIONES_PERMITIDAS)}"
            )

        # Las copias pdf/ y markdown/ se nombran por nombre base: otro original con el mismo
        # nombre base y distinta extensión (norma.docx / norma.pdf) comparte esas copias.
        hermanos = sorted(
            p.name for p in settings.ORIGINALES_DIR.glob(glob.escape(Path(seguro).stem) + ".*")
            if p.name != seguro and not p.name.startswith(".")
        ) if settings.ORIGINALES_DIR.exists() else []

        # El upload se convierte desde un área temporal y solo se promueve a originales/ si la
        # conversión funciona: un archivo rechazado no ensucia originales/ ni pisa uno válido.
        settings.ORIGINALES_DIR.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=settings.ORIGINALES_DIR, prefix=".staging-") as staging:
            recibido = _recibir_en(Path(staging), archivo, seguro)
            conversion = convertir(recibido)
            original = settings.ORIGINALES_DIR / seguro
            os.replace(recibido, original)
        rutas.original = _relativa(original)
        rutas.pdf = _relativa(conversion.pdf)
        rutas.markdown = _relativa(conversion.markdown)

        estado, chunks = rag.indexar_archivo(conversion.markdown)
        aviso = (f"Comparte nombre base con {', '.join(hermanos)}: las copias PDF/Markdown "
                 "de ese archivo fueron reemplazadas por las de este.") if hermanos else None
        return ResultadoArchivo(nombre=nombre, rutas=rutas, chunks_indexados=chunks, estado=estado,
                                detalle=aviso)
    except (ErrorArchivo, ConversionError) as e:
        detalle = str(e)
    except Exception as e:  # cualquier otro fallo del archivo no debe abortar el lote
        detalle = f"{type(e).__name__}: {e}"
    return ResultadoArchivo(nombre=nombre, rutas=rutas, estado=ESTADO_ERROR, detalle=detalle)


@router.post("/subir", response_model=RespuestaSubida)
def subir_documentos(
    archivos: list[UploadFile] = File(default=[], description="Uno o varios archivos: PDF, DOCX, PPTX, TXT, MD"),
    files: list[UploadFile] = File(default=[], description="Alias de `archivos`"),
    rag: RAGService = Depends(get_rag_service),
    _: Usuario = Depends(requiere_rol("docente", "admin")),
):
    """Guarda cada archivo en originales/, genera sus copias PDF y Markdown y reindexa el RAG
    de forma incremental. Cada archivo se procesa de forma independiente. Solo docente/admin: subir material
    de la base documental no es una acción de estudiante."""
    todos = [*archivos, *files]
    if not todos:
        raise HTTPException(status_code=422, detail="No se recibió ningún archivo (campo `archivos`).")

    resultados = [_procesar_archivo(a, rag) for a in todos]
    return RespuestaSubida(
        resultados=resultados,
        resumen=ResumenLote(
            total=len(resultados),
            indexados=sum(r.estado == "indexado" for r in resultados),
            omitidos_sin_cambios=sum(r.estado == "omitido_sin_cambios" for r in resultados),
            errores=sum(r.estado == ESTADO_ERROR for r in resultados),
        ),
    )


@router.post("/reindexar")
def reindexar(rag: RAGService = Depends(get_rag_service), _: Usuario = Depends(requiere_rol("docente", "admin"))):
    """Mantenimiento: reconstruye por completo base_vectorial/ desde documentacion/markdown/. Solo docente/admin."""
    return rag.reconstruir()


@router.get("")
def listar_documentos(rag: RAGService = Depends(get_rag_service)):
    """Documentos de documentacion/markdown/ con su estado en el índice."""
    indice = {d["nombre_archivo"]: d for d in rag.resumen_indice()["documentos"]}
    documentos = []
    for md in sorted(settings.MARKDOWN_DIR.glob("*.md")) if settings.MARKDOWN_DIR.exists() else []:
        info = indice.get(md.name)
        original = next(iter(sorted(settings.ORIGINALES_DIR.glob(glob.escape(md.stem) + ".*"))), None) \
            if settings.ORIGINALES_DIR.exists() else None
        pdf = settings.PDF_DIR / f"{md.stem}.pdf"
        documentos.append({
            "nombre": md.name,
            "indexado": info is not None,
            "chunks": info["chunks"] if info else 0,
            "fecha_indexado": info["fecha_indexado"] if info else None,
            "archivos": {
                "original": original.name if original else None,
                "pdf": pdf.name if pdf.exists() else None,
                "markdown": md.name,
            },
        })
    return {"total_chunks": rag.contar_chunks(), "documentos": documentos}
