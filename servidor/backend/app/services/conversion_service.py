"""Conversión de documentos subidos a PDF y Markdown.

Solo librerías pip, locales y gratuitas (sin binarios externos):
  - a Markdown: markitdown (PDF / DOCX / PPTX); TXT y MD se leen directamente.
  - a PDF: reportlab. Si el original ya es PDF se copia tal cual; en el resto de
    formatos el PDF es una re-renderización del Markdown (texto, encabezados,
    listas, tablas simples), no una copia visual fiel del original.
"""
import os
import re
import shutil
import textwrap
import zipfile
from dataclasses import dataclass
from pathlib import Path

from app.core.config import settings


class ConversionError(Exception):
    """Falla controlada de conversión (mensaje apto para mostrar al usuario)."""


@dataclass
class Conversion:
    pdf: Path
    markdown: Path


def decodificar_texto(datos: bytes) -> str:
    """Decodifica bytes de un archivo de texto probando UTF-8 y cp1252."""
    for codificacion in ("utf-8-sig", "cp1252"):
        try:
            return datos.decode(codificacion)
        except UnicodeDecodeError:
            continue
    return datos.decode("utf-8", errors="replace")


# ---------------------------------------------------------------------------
# Origen -> Markdown
# ---------------------------------------------------------------------------

_markitdown = None


def _validar_formato(origen: Path) -> None:
    """markitdown detecta el tipo por contenido y trata como texto plano un .docx/.pdf corrupto;
    se comprueba antes que el archivo realmente tenga la estructura que dice su extensión."""
    extension = origen.suffix.lower()
    with open(origen, "rb") as f:
        cabecera = f.read(4096)
    if extension == ".pdf" and b"%PDF-" not in cabecera[:1024]:
        raise ConversionError("el archivo no es un PDF válido")
    if extension in (".docx", ".pptx") and not zipfile.is_zipfile(origen):
        raise ConversionError(f"el archivo no es un {extension[1:].upper()} válido")
    if extension in (".md", ".txt") and b"\x00" in cabecera:
        raise ConversionError("el archivo no parece texto (contiene datos binarios)")


def _a_markdown(origen: Path) -> str:
    extension = origen.suffix.lower()
    _validar_formato(origen)
    if extension in (".md", ".txt"):
        return decodificar_texto(origen.read_bytes())

    global _markitdown
    if _markitdown is None:
        from markitdown import MarkItDown
        _markitdown = MarkItDown()
    try:
        return _markitdown.convert(str(origen)).text_content or ""
    except Exception as e:
        raise ConversionError(f"No se pudo leer el {extension[1:].upper()}: {e}") from e


# ---------------------------------------------------------------------------
# Markdown -> PDF (reportlab)
# ---------------------------------------------------------------------------

_FUENTE = "Helvetica"
_FUENTE_NEGRITA = "Helvetica-Bold"
_FUENTES_LISTAS = False

_SUSTITUCIONES = {
    "→": "->", "←": "<-", "≥": ">=", "≤": "<=",
    " ": " ", "​": "", "﻿": "",
}


def _registrar_fuentes() -> None:
    """Registra Vera (viene con reportlab: acentos y ñ); si falla, queda Helvetica."""
    global _FUENTE, _FUENTE_NEGRITA, _FUENTES_LISTAS
    if _FUENTES_LISTAS:
        return
    _FUENTES_LISTAS = True
    try:
        import reportlab
        from reportlab.lib.fonts import addMapping
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont

        carpeta = Path(reportlab.__file__).parent / "fonts"
        for nombre, archivo in (("Vera", "Vera.ttf"), ("Vera-Bold", "VeraBd.ttf"),
                                ("Vera-Italic", "VeraIt.ttf"), ("Vera-BoldItalic", "VeraBI.ttf")):
            pdfmetrics.registerFont(TTFont(nombre, str(carpeta / archivo)))
        addMapping("Vera", 0, 0, "Vera")
        addMapping("Vera", 1, 0, "Vera-Bold")
        addMapping("Vera", 0, 1, "Vera-Italic")
        addMapping("Vera", 1, 1, "Vera-BoldItalic")
        _FUENTE, _FUENTE_NEGRITA = "Vera", "Vera-Bold"
    except Exception:
        pass


def _sanear(texto: str) -> str:
    """Reemplaza caracteres que la fuente del PDF no puede dibujar."""
    from reportlab.pdfbase import pdfmetrics

    try:
        cmap = pdfmetrics.getFont(_FUENTE).face.charToGlyph
    except AttributeError:
        cmap = {i: 1 for i in range(256)}  # Helvetica: Latin-1
    salida = []
    for c in texto:
        if c in "\n\t" or ord(c) in cmap:
            salida.append(c)
        else:
            salida.append(_SUSTITUCIONES.get(c, "?"))
    return "".join(salida)


def _inline(texto: str) -> str:
    """Markdown en línea -> mini-markup de reportlab (con escape XML)."""
    codigos: list[str] = []

    def guardar_codigo(m):
        codigos.append(m.group(1))
        return f"\x00{len(codigos) - 1}\x00"

    texto = re.sub(r"`([^`]+)`", guardar_codigo, texto)
    texto = texto.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    texto = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", texto)
    texto = re.sub(r"\*\*(.+?)\*\*|__(.+?)__", lambda m: f"<b>{m.group(1) or m.group(2)}</b>", texto)
    texto = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<i>\1</i>", texto)
    texto = re.sub(r"(?<![\w_])_(?!\s)(.+?)(?<!\s)_(?![\w_])", r"<i>\1</i>", texto)

    def poner_codigo(m):
        codigo = codigos[int(m.group(1))].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        return f'<font name="Courier">{codigo}</font>'

    return re.sub(r"\x00(\d+)\x00", poner_codigo, texto)


def _renderizar_pdf(markdown: str, destino: Path, titulo: str) -> None:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import (HRFlowable, Paragraph, Preformatted,
                                    SimpleDocTemplate, Spacer, Table, TableStyle)

    _registrar_fuentes()
    markdown = _sanear(markdown.replace("\r\n", "\n").replace("\r", "\n"))
    titulo = _sanear(titulo)

    base = ParagraphStyle("base", fontName=_FUENTE, fontSize=10, leading=14,
                          alignment=TA_LEFT, spaceAfter=6)
    encabezados = {
        n: ParagraphStyle(f"h{n}", parent=base, fontName=_FUENTE_NEGRITA,
                          fontSize=tam, leading=tam + 4, spaceBefore=10, spaceAfter=6)
        for n, tam in zip(range(1, 7), (20, 16, 13, 11.5, 10.5, 10))
    }
    codigo = ParagraphStyle("codigo", parent=base, fontName="Courier", fontSize=8.5,
                            leading=11, backColor=colors.HexColor("#f1f5f9"),
                            borderPadding=4, spaceBefore=4, spaceAfter=8)
    celda = ParagraphStyle("celda", parent=base, fontSize=8.5, leading=11, spaceAfter=0)
    celda_cab = ParagraphStyle("celda_cab", parent=celda, fontName=_FUENTE_NEGRITA)
    cita = ParagraphStyle("cita", parent=base, leftIndent=14, textColor=colors.HexColor("#475569"))

    def parrafo(texto: str, estilo, **kw):
        try:
            return Paragraph(_inline(texto), estilo, **kw)
        except Exception:  # markup desbalanceado: se dibuja como texto plano
            plano = texto.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            return Paragraph(plano, estilo, **kw)

    def tabla(filas: list[list[str]]):
        columnas = max(len(f) for f in filas)
        datos = [[parrafo(c, celda_cab if i == 0 else celda) for c in f + [""] * (columnas - len(f))]
                 for i, f in enumerate(filas)]
        ancho = (A4[0] - 4 * cm) / columnas
        t = Table(datos, colWidths=[ancho] * columnas, repeatRows=1)
        t.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#94a3b8")),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        return t

    flujo = []
    parrafo_actual: list[str] = []
    lineas = markdown.split("\n")
    i = 0

    def cerrar_parrafo():
        if parrafo_actual:
            flujo.append(parrafo(" ".join(parrafo_actual), base))
            parrafo_actual.clear()

    while i < len(lineas):
        linea = lineas[i]
        s = linea.strip()

        if s.startswith("```") or s.startswith("~~~"):
            cerrar_parrafo()
            bloque = []
            i += 1
            while i < len(lineas) and not lineas[i].strip().startswith(("```", "~~~")):
                bloque.append(lineas[i])
                i += 1
            texto = "\n".join(textwrap.fill(l, 95, replace_whitespace=False, drop_whitespace=False)
                              if len(l) > 95 else l for l in bloque)
            flujo.append(Preformatted(texto.encode("cp1252", "replace").decode("cp1252"), codigo))
        elif not s:
            cerrar_parrafo()
        elif re.fullmatch(r"(-{3,}|\*{3,}|_{3,})", s):
            cerrar_parrafo()
            flujo.append(HRFlowable(width="100%", color=colors.HexColor("#cbd5e1"), spaceAfter=6))
        elif m := re.match(r"(#{1,6})\s+(.*?)\s*#*$", s):
            cerrar_parrafo()
            flujo.append(parrafo(m.group(2), encabezados[len(m.group(1))]))
        elif s.startswith("|"):
            cerrar_parrafo()
            filas = []
            while i < len(lineas) and lineas[i].strip().startswith("|"):
                fila = lineas[i].strip().strip("|")
                if not re.fullmatch(r"[\s:|-]+", fila):  # descarta la fila |---|---|
                    filas.append([c.strip() for c in fila.split("|")])
                i += 1
            i -= 1
            if filas:
                flujo.append(tabla(filas))
                flujo.append(Spacer(1, 6))
        elif m := re.match(r"(\s*)([-*+]|\d+[.)])\s+(.*)", linea):
            cerrar_parrafo()
            sangria = 14 + 14 * (len(m.group(1).replace("\t", "    ")) // 2)
            marca = "•" if m.group(2) in "-*+" else m.group(2)
            flujo.append(parrafo(m.group(3), ParagraphStyle(
                "item", parent=base, leftIndent=sangria, bulletIndent=sangria - 12, spaceAfter=2),
                bulletText=marca))
        elif s.startswith(">"):
            cerrar_parrafo()
            flujo.append(parrafo(s.lstrip("> "), cita))
        else:
            parrafo_actual.append(s)
        i += 1
    cerrar_parrafo()

    if not flujo:
        raise ConversionError("sin texto extraíble")

    def pie(canvas, doc):
        canvas.saveState()
        canvas.setFont(_FUENTE, 8)
        canvas.setFillColor(colors.HexColor("#64748b"))
        canvas.drawRightString(A4[0] - 2 * cm, 1.2 * cm, f"{doc.page}")
        canvas.restoreState()

    doc = SimpleDocTemplate(str(destino), pagesize=A4, title=titulo or "Documento",
                            leftMargin=2 * cm, rightMargin=2 * cm, topMargin=2 * cm, bottomMargin=2 * cm)
    doc.build(flujo, onFirstPage=pie, onLaterPages=pie)


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------

def convertir(origen: Path, pdf_dir: Path | None = None, markdown_dir: Path | None = None) -> Conversion:
    """Genera la copia PDF y la copia Markdown de `origen`.

    Escribe primero a temporales y reemplaza al final, para no dejar archivos
    parciales si algo falla a mitad de la conversión.
    """
    pdf_dir = Path(pdf_dir or settings.PDF_DIR)
    markdown_dir = Path(markdown_dir or settings.MARKDOWN_DIR)
    pdf_dir.mkdir(parents=True, exist_ok=True)
    markdown_dir.mkdir(parents=True, exist_ok=True)

    extension = origen.suffix.lower()
    if extension not in settings.EXTENSIONES_PERMITIDAS:
        raise ConversionError(f"Extensión no soportada: {extension or '(sin extensión)'}")

    destino_pdf = pdf_dir / f"{origen.stem}.pdf"
    destino_md = markdown_dir / f"{origen.stem}.md"
    tmp_pdf = destino_pdf.with_name(f".{destino_pdf.name}.tmp")
    tmp_md = destino_md.with_name(f".{destino_md.name}.tmp")

    try:
        texto = _a_markdown(origen)
        if not texto.strip():
            raise ConversionError("sin texto extraíble (¿PDF escaneado o archivo vacío? no hay OCR)")

        # Markdown: si el original ya es .md se conserva idéntico
        if extension == ".md":
            shutil.copyfile(origen, tmp_md)
        else:
            tmp_md.write_text(texto, encoding="utf-8")

        # PDF: si el original ya es .pdf se conserva idéntico
        if extension == ".pdf":
            shutil.copyfile(origen, tmp_pdf)
        else:
            _renderizar_pdf(texto, tmp_pdf, titulo=origen.stem.replace("_", " "))

        os.replace(tmp_md, destino_md)
        os.replace(tmp_pdf, destino_pdf)
    except ConversionError:
        raise
    except Exception as e:
        raise ConversionError(f"Falló la conversión: {e}") from e
    finally:
        tmp_md.unlink(missing_ok=True)
        tmp_pdf.unlink(missing_ok=True)

    return Conversion(pdf=destino_pdf, markdown=destino_md)
