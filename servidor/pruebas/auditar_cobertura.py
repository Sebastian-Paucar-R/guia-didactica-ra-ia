"""Auditoría de cobertura: ¿qué temas del sílabo tienen documentación indexada que los respalde?

Para cada tema de configuracion/silabo.yaml busca sus palabras clave en el texto de los fragmentos que
realmente están en el índice vectorial (Chroma), no solo en los archivos .md de la carpeta: un documento
que existe pero no se indexó no respalda nada. El resultado es reportes/cobertura_silabo.md (tabla) y
reportes/cobertura_silabo.json (lo lee evaluar_tutor.py para cruzar cobertura con respuestas).

Estados:
  cubierto       algún documento asociado al tema (campo `archivos` del YAML) está indexado y menciona al
                 menos 3 de sus palabras clave distintas en 2 o más fragmentos.
  parcial        hay texto indexado que menciona el tema pero no alcanza para "cubierto": menciones sueltas
                 en documentos de otros temas, o un documento asociado que apenas lo toca.
  sin cobertura  ningún fragmento indexado menciona el tema (o sus archivos asociados no están indexados):
                 el tutor no tiene de dónde responderlo y dirá que no está en los documentos.

Uso (desde servidor/):  python pruebas/auditar_cobertura.py [--base-vectorial DIR] [--salida-md ...] [--salida-json ...]
No modifica el índice real (trabaja sobre una copia temporal). Conviene ejecutarlo con el índice al día
(el servidor lo sincroniza al arrancar).
"""
import argparse
import json
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path

SERVIDOR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVIDOR / "backend"))

from app.core import silabo  # noqa: E402
from app.core.config import settings  # noqa: E402

COLECCION = "langchain"
MIN_CLAVES = 3         # palabras clave distintas que un documento asociado debe mencionar para "cubrir" un tema
MIN_FRAGMENTOS = 2     # y en cuántos fragmentos distintos (no proporcional: las listas incluyen sinónimos que un
                       # documento bueno no usa todos)


def leer_indice(base_vectorial: Path) -> dict[str, list[str]]:
    """{nombre_archivo: [texto de cada fragmento indexado]} leído de Chroma.

    Chroma reescribe archivos del índice (chroma.sqlite3, *.bin) con solo abrirlo, y base_vectorial/ está
    versionada en git: por eso se lee una copia temporal y el índice real no se toca."""
    import chromadb
    from chromadb.config import Settings as ChromaSettings

    if not (base_vectorial / "chroma.sqlite3").is_file():
        raise SystemExit(f"No hay un índice Chroma en {base_vectorial}")
    with tempfile.TemporaryDirectory(prefix="auditoria_indice_", ignore_cleanup_errors=True) as tmp:
        copia = Path(tmp) / "indice"
        shutil.copytree(base_vectorial, copia)
        cliente = chromadb.PersistentClient(path=str(copia), settings=ChromaSettings(anonymized_telemetry=False))
        try:
            coleccion = cliente.get_collection(COLECCION)
        except Exception as e:
            raise SystemExit(f"No hay colección '{COLECCION}' en {base_vectorial}: {e}")
        datos = coleccion.get(include=["documents", "metadatas"])
        del coleccion, cliente
        try:
            cerrar = chromadb.api.client.SharedSystemClient.clear_system_cache
            cerrar()   # suelta los archivos de la copia para poder borrarla en Windows
        except Exception:
            pass
    por_archivo: dict[str, list[str]] = {}
    for texto, meta in zip(datos["documents"], datos["metadatas"]):
        por_archivo.setdefault(meta["nombre_archivo"], []).append(texto)
    return por_archivo


def evaluar_tema(tema, indice: dict[str, list[str]]) -> dict:
    """Qué documentos indexados mencionan el tema y qué estado le corresponde."""
    fuertes = [(k, regex) for k, regex, _, debil in tema._patrones if not debil]   # las débiles ("norma ISO") no prueban nada
    normalizados = {doc: [silabo.normalizar(f) for f in fragmentos] for doc, fragmentos in indice.items()}

    menciones = []
    for doc, fragmentos in normalizados.items():
        claves = {k for k, regex in fuertes for f in fragmentos if regex.search(f)}
        if not claves:
            continue
        n_frag = sum(any(regex.search(f) for _, regex in fuertes) for f in fragmentos)
        menciones.append({"documento": doc, "claves": sorted(claves), "fragmentos": n_frag,
                          "asociado": doc in tema.archivos})
    menciones.sort(key=lambda m: (not m["asociado"], -len(m["claves"]), -m["fragmentos"], m["documento"]))

    asociados_indexados = [a for a in tema.archivos if a in indice]
    faltan = [a for a in tema.archivos if a not in indice]
    respaldo = [m for m in menciones if m["asociado"] and len(m["claves"]) >= MIN_CLAVES and m["fragmentos"] >= MIN_FRAGMENTOS]
    if respaldo:
        estado = "cubierto"
    elif menciones:
        estado = "parcial"
    else:
        estado = "sin cobertura"
    return {
        "id": tema.id, "tema": tema.nombre, "unidad": tema.unidad, "complementario": tema.complementario,
        "archivos_asociados": list(tema.archivos), "asociados_indexados": asociados_indexados,
        "asociados_sin_indexar": faltan, "claves_totales": len(fuertes), "claves_minimas": MIN_CLAVES,
        "documentos": menciones, "estado": estado,
    }


def _celda_documentos(fila: dict) -> str:
    if not fila["documentos"]:
        detalle = "—"
    else:
        detalle = "<br>".join(
            f"{'**' if m['asociado'] else ''}{m['documento'].removesuffix('.md')}{'**' if m['asociado'] else ''} "
            f"({len(m['claves'])} {'término' if len(m['claves']) == 1 else 'términos'}, {m['fragmentos']} fragm.)"
            for m in fila["documentos"][:4]
        ) + (f"<br>y {len(fila['documentos']) - 4} más" if len(fila["documentos"]) > 4 else "")
    if fila["asociados_sin_indexar"]:
        detalle += "<br>⚠ asociado sin indexar: " + ", ".join(a.removesuffix(".md") for a in fila["asociados_sin_indexar"])
    return detalle


def escribir_md(filas: list[dict], indice: dict[str, list[str]], en_disco: set[str], ruta: Path, base: Path) -> None:
    conteo = {e: sum(f["estado"] == e for f in filas) for e in ("cubierto", "parcial", "sin cobertura")}
    total_fragmentos = sum(len(v) for v in indice.values())
    marca = {"cubierto": "✅ cubierto", "parcial": "🟡 parcial", "sin cobertura": "❌ sin cobertura"}
    huerfanos = sorted(d for d in indice if not any(d in f["archivos_asociados"] for f in filas))
    sin_indexar = sorted(en_disco - set(indice))

    out = [
        "# Cobertura del sílabo por la documentación indexada",
        "",
        f"Generado por `pruebas/auditar_cobertura.py` el {datetime.now():%Y-%m-%d %H:%M}. "
        f"Sílabo: `configuracion/silabo.yaml` ({len(filas)} temas, 4 unidades). "
        f"Índice: `{base.name}/` con {len(indice)} documentos y {total_fragmentos} fragmentos.",
        "",
        f"**Resumen:** {conteo['cubierto']} cubiertos · {conteo['parcial']} parciales · "
        f"{conteo['sin cobertura']} sin cobertura (de {len(filas)} temas).",
        "",
        "| Tema | Unidad | Documentos disponibles | Estado |",
        "|---|---|---|---|",
    ]
    for f in filas:
        nombre = f"**{f['id']}** {f['tema']}" + (" _(complementario)_" if f["complementario"] else "")
        out.append(f"| {nombre} | {f['unidad']} | {_celda_documentos(f)} | {marca[f['estado']]} |")

    out += ["", "## Temas que el tutor no podrá responder (sin cobertura)", ""]
    sin = [f for f in filas if f["estado"] == "sin cobertura"]
    out += [f"- **{f['id']}** {f['tema']} (Unidad {f['unidad']})" for f in sin] or ["- Ninguno."]
    out += ["", "## Temas con cobertura parcial", "",
            "Hay texto indexado que los menciona, pero no un documento dedicado: el tutor podrá dar, como mucho, "
            "lo que diga esa mención y deberá declarar que el resto no está en los documentos.", ""]
    parciales = [f for f in filas if f["estado"] == "parcial"]
    out += [f"- **{f['id']}** {f['tema']} (Unidad {f['unidad']})" for f in parciales] or ["- Ninguno."]

    out += ["", "## Cómo se decide el estado", "",
            f"- Se buscan las palabras clave del tema (las fuertes; las marcadas `~` en el YAML no cuentan) en el texto "
            f"de cada fragmento **indexado**, sin acentos ni mayúsculas y por palabra completa.",
            f"- **cubierto**: un documento asociado al tema en el YAML menciona al menos {MIN_CLAVES} palabras clave "
            f"distintas del tema en {MIN_FRAGMENTOS} o más fragmentos. **parcial**: hay menciones pero no llegan a eso "
            "(incluye los temas que ningún documento trata de forma dedicada). "
            "**sin cobertura**: ninguna mención en el índice.",
            "- En la columna de documentos, **negrita** = documento asociado al tema en el YAML; entre paréntesis, "
            "cuántas palabras clave distintas y en cuántos fragmentos aparecen.",
            "- Es una medida léxica: comprueba que el tema se nombra en la documentación, no que la explicación sea "
            "buena. Un tema \"cubierto\" puede seguir respondiéndose mal si la recuperación trae otros fragmentos.",
            ""]
    if huerfanos:
        out += ["## Documentos indexados no asociados a ningún tema", ""] + [f"- {d}" for d in huerfanos] + [""]
    if sin_indexar:
        out += ["## ⚠ Documentos en `documentacion/markdown/` que NO están indexados", ""] + [f"- {d}" for d in sin_indexar] + [""]
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text("\n".join(out), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base-vectorial", type=Path, default=settings.BASE_VECTORIAL_DIR)
    ap.add_argument("--markdown", type=Path, default=settings.MARKDOWN_DIR)
    ap.add_argument("--salida-md", type=Path, default=SERVIDOR / "reportes" / "cobertura_silabo.md")
    ap.add_argument("--salida-json", type=Path, default=SERVIDOR / "reportes" / "cobertura_silabo.json")
    args = ap.parse_args()

    indice = leer_indice(args.base_vectorial)
    en_disco = {p.name for p in args.markdown.glob("*.md")}
    filas = [evaluar_tema(t, indice) for t in silabo.temas()]

    escribir_md(filas, indice, en_disco, args.salida_md, args.base_vectorial)
    args.salida_json.write_text(json.dumps({
        "generado": datetime.now().isoformat(timespec="seconds"),
        "documentos_indexados": sorted(indice), "fragmentos": sum(len(v) for v in indice.values()),
        "temas": filas,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    for f in filas:
        print(f"{f['estado']:14} {f['id']:4} {f['tema'][:70]}")
    print(f"\nEscrito {args.salida_md}\nEscrito {args.salida_json}")


if __name__ == "__main__":
    main()
