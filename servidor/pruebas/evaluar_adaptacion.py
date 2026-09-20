"""Evalúa la adaptación del tutor al estudiante de punta a punta contra el servidor real (POST /api/v1/chat y /perfil).

Tres partes (casos en pruebas/casos_adaptacion.json):

1. **Misma pregunta, tres estudiantes.** Un novato, un estudiante nuevo y un avanzado hacen cada pregunta. Las respuestas
   deben diferir en la forma (extensión, andamiaje, estilo, cierre) y coincidir en el contenido normativo: las mismas
   ideas de la norma y ninguna norma, año o cláusula que no esté en los documentos indexados.
2. **Caché segmentado.** Cada estudiante repite su pregunta en una conversación nueva: quien comparte ajuste recibe lo
   guardado (`desde_cache`), quien tiene otro no recibe la respuesta de otro, y lo personal (cita lo ya trabajado) no
   se guarda.
3. **Evolución.** Un estudiante sin perfil sembrado dice que no entiende y pide ejemplos; el perfil (GET /perfil y
   /progreso) debe moverse poco a poco y solo por lo que hace.

Los verdicts automáticos son HEURÍSTICOS (regex y similitud de texto): sirven para no pasar por alto un fallo grosero, no
para dar por buena una respuesta. Las tres respuestas van lado a lado en el informe para leerlas.

Uso: el servidor y este script deben compartir la base de perfiles (se siembran los tres perfiles en ella) y conviene un
caché vacío y una copia del índice para no tocar los datos reales:

    BASE_VECTORIAL_DIR=<copia> CACHE_DB_PATH=<nuevo> PERFIL_DB_PATH=<nuevo> PYTHONUTF8=1 \
        python -m uvicorn app.main:app --app-dir backend                     (desde servidor/, PYTHONPATH=backend)
    PERFIL_DB_PATH=<el mismo> python pruebas/evaluar_adaptacion.py [--url http://127.0.0.1:8000] [--etiqueta "texto"]

Guarda reportes/evaluacion_adaptacion.json y reportes/evaluacion_adaptacion.md.
"""
import argparse
import difflib
import json
import os
import re
import sys
import textwrap
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from evaluar_tutor import _NORMA, _http, _numeros_indexados  # noqa: E402
from app.models.perfil import PerfilEstudiante  # noqa: E402
from app.services.perfil_service import PerfilService  # noqa: E402

ORDEN = ("novato", "estandar", "avanzado")
UMBRAL_SIMILITUD = 0.80      # dos respuestas más parecidas que esto no difieren en la forma
PASO_MAXIMO = 0.4            # lo máximo que puede bajar el nivel un solo mensaje

# Marcas de la forma que se pide a cada perfil (heurísticas, para orientar la lectura)
_ANALOGIA = re.compile(r"\b(?:por ejemplo|imagina\w*|piensa en|es como|como si|supón\w*|suponte|analog[ií]a|situaci[oó]n|"
                       r"equipo|proyecto|cotidian\w*)\b", re.IGNORECASE)
_SOCRATICA = re.compile(r"\b(?:por qu[eé]|qu[eé] (?:pasar[ií]a|ocurrir[ií]a|suceder[ií]a)|c[oó]mo (?:se relaciona|justificar[ií]as|"
                        r"argumentar[ií]as)|en qu[eé] (?:se diferencia|casos)|qu[eé] (?:riesgo|relaci[oó]n)|frente a|a diferencia)\b",
                        re.IGNORECASE)


# ---------------------------------------------------------------------------------------------- HTTP

def chat(url: str, mensaje: str, user_id: str | None, conversation_id: str, timeout: float) -> dict:
    """Una consulta al chat. Nunca lanza: un fallo de red o del servidor queda como tipo 'error_http'."""
    cuerpo = {"message": mensaje, "conversation_id": conversation_id}
    if user_id:
        cuerpo["user_id"] = user_id
    try:
        d = _http(f"{url}/api/v1/chat", cuerpo, timeout)
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as e:
        d = {"response": f"{type(e).__name__}: {e}", "tipo": "error_http"}
    return {"respuesta": d.get("response", ""), "tipo": d.get("tipo", "error_http"), "desde_cache": bool(d.get("desde_cache")),
            "ms": d.get("tiempo_respuesta_ms"), "adaptacion": d.get("adaptacion"), "ubicacion": d.get("ubicacion")}


def post_vacio(url: str, timeout: float) -> dict:
    peticion = urllib.request.Request(url, data=b"", method="POST", headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(peticion, timeout=timeout) as r:
        return json.load(r)


def sembrar(perfiles: PerfilService, user_id: str, definicion: dict) -> None:
    """Deja al estudiante con exactamente el perfil del caso (historial limpio) antes de cada pregunta."""
    perfiles.reiniciar(user_id)
    perfiles.guardar(PerfilEstudiante(user_id=user_id, **definicion["perfil"]))


# ---------------------------------------------------------------------------------------------- análisis

def palabras(texto: str) -> int:
    return len(texto.split())


def identificadores(texto: str) -> list[str]:
    """Normas citadas en la respuesta (ISO/IEC/IEEE + número, año)."""
    return sorted({re.sub(r"\s+", " ", m.group(0)).strip().upper() for m in _NORMA.finditer(texto)})


def no_respaldados(texto: str, pregunta: str, numeros_docs: set[str]) -> list[str]:
    """Normas o años de la respuesta que no están en los documentos indexados ni en la pregunta."""
    validos = numeros_docs | set(re.findall(r"\d{3,6}", pregunta))
    malos = []
    for m in _NORMA.finditer(texto):
        if m.group(1) not in validos or (m.group(2) and m.group(2) not in validos):
            malos.append(m.group(0).strip())
    return malos


def tiene_ancla(texto: str, alternativas: list[str]) -> bool:
    bajo = texto.lower()
    return any(a.lower() in bajo for a in alternativas)


def similitud(a: str, b: str) -> float:
    return round(difflib.SequenceMatcher(None, a, b).ratio(), 2)


# ---------------------------------------------------------------------------------------------- parte 1 y 2

def parte_misma_pregunta(url, perfiles, casos, run, numeros_docs, timeout) -> list[dict]:
    salida = []
    for p in casos["preguntas"]:
        fila = {"id": p["id"], "pregunta": p["pregunta"], "tema_id": p["tema_id"], "primera": {}, "segunda": {}}
        for est in ORDEN:
            uid = f"eval-adap-{run}-{est}"
            sembrar(perfiles, uid, casos["estudiantes"][est])
            fila["primera"][est] = chat(url, p["pregunta"], uid, f"conv-{run}-{est}-{p['id']}-1", timeout)
            print(f"[1] {p['id']} {est:9} tipo={fila['primera'][est]['tipo']:11} "
                  f"seg={(fila['primera'][est]['adaptacion'] or {}).get('segmento', '-')!r:34} "
                  f"{(fila['primera'][est]['ms'] or 0) / 1000:5.1f}s  {palabras(fila['primera'][est]['respuesta'])} palabras", flush=True)
        # Segunda vez, conversación nueva: quién recibe lo guardado. Un anónimo (sin user_id) comparte lo del perfil neutro.
        for est in ORDEN:
            uid = f"eval-adap-{run}-{est}"
            sembrar(perfiles, uid, casos["estudiantes"][est])
            fila["segunda"][est] = chat(url, p["pregunta"], uid, f"conv-{run}-{est}-{p['id']}-2", timeout)
        fila["segunda"]["anonimo"] = chat(url, p["pregunta"], None, f"conv-{run}-anon-{p['id']}-2", timeout)
        print(f"[2] {p['id']} desde_cache: " + " ".join(f"{k}={'sí' if v['desde_cache'] else 'no'}" for k, v in fila["segunda"].items()),
              flush=True)
        fila["analisis"] = analizar(p, fila, numeros_docs)
        salida.append(fila)
    return salida


def analizar(p: dict, fila: dict, numeros_docs: set[str]) -> dict:
    r = fila["primera"]
    textos = {e: r[e]["respuesta"] for e in ORDEN}
    tipos_ok = all(r[e]["tipo"] == "respuesta" for e in ORDEN)
    ids = {e: identificadores(t) for e, t in textos.items()}
    malos = {e: no_respaldados(t, p["pregunta"], numeros_docs) for e, t in textos.items()}
    anclas_falta = {e: [a[0] for a in p["anclas"] if not tiene_ancla(t, a)] for e, t in textos.items()}
    contradichas = {e: [x for x in p.get("prohibido", []) if re.search(x, t, re.IGNORECASE)] for e, t in textos.items()}
    pares = {f"{a}~{b}": similitud(textos[a], textos[b]) for i, a in enumerate(ORDEN) for b in ORDEN[i + 1:]}
    segmentos = {e: (r[e]["adaptacion"] or {}).get("segmento") for e in ORDEN}
    # Caché: lo que cada uno recibió la segunda vez frente a lo que se generó la primera
    s = fila["segunda"]
    propias = {e: s[e]["respuesta"] == r[e]["respuesta"] for e in ORDEN}
    ajenas = {e: [o for o in ORDEN if o != e and s[e]["respuesta"] == r[o]["respuesta"] and r[o]["respuesta"] != r[e]["respuesta"]]
              for e in ORDEN}
    personal = {e: bool((r[e]["adaptacion"] or {}).get("referencias")) for e in ORDEN}
    esperado_cache = {e: not personal[e] for e in ORDEN}
    cierra_avanzado = textos["avanzado"].rstrip().endswith("?")
    return {
        "tipos_ok": tipos_ok, "identificadores": ids, "no_respaldados": malos, "anclas_que_faltan": anclas_falta,
        "afirmaciones_contradichas": contradichas,
        "palabras": {e: palabras(t) for e, t in textos.items()}, "similitud_entre_pares": pares, "segmentos": segmentos,
        "marca_analogia": {e: bool(_ANALOGIA.search(t)) for e, t in textos.items()},
        "marca_socratica_avanzado": bool(_SOCRATICA.search(textos["avanzado"])), "cierra_en_pregunta_avanzado": cierra_avanzado,
        "referencias": {e: [x["tema_id"] for x in (r[e]["adaptacion"] or {}).get("referencias", [])] for e in ORDEN},
        "cache": {e: s[e]["desde_cache"] for e in list(ORDEN) + ["anonimo"]},
        "cache_esperado": esperado_cache, "recibio_lo_suyo": propias, "recibio_lo_de_otro": ajenas,
        "anonimo_recibe_lo_del_estandar": s["anonimo"]["respuesta"] == r["estandar"]["respuesta"],
        "verdictos": {
            "contenido_normativo": tipos_ok and not any(malos.values()) and not any(anclas_falta.values())
            and not any(contradichas.values()),
            "forma_distinta": tipos_ok and all(v < UMBRAL_SIMILITUD for v in pares.values())
            and palabras(textos["novato"]) > palabras(textos["avanzado"]),
            "ajustes_distintos": len({v for v in segmentos.values()}) == 3,
            "cache_por_segmento": all(s[e]["desde_cache"] == esperado_cache[e] for e in ORDEN) and s["anonimo"]["desde_cache"]
            and not any(ajenas.values()) and (s["anonimo"]["respuesta"] == r["estandar"]["respuesta"]),
        },
    }


# ---------------------------------------------------------------------------------------------- parte 3

def parte_evolucion(url: str, casos: dict, run: str, timeout: float) -> dict:
    ev = casos["evolucion"]
    uid, conv = f"eval-evol-{run}", f"conv-evol-{run}"
    post_vacio(f"{url}/api/v1/perfil/{uid}/reiniciar", timeout)
    inicial = _http(f"{url}/api/v1/perfil/{uid}", None, timeout)
    pasos = [{"turno": 0, "mensaje": "(perfil inicial)", "nivel_u2": inicial["nivel_por_unidad"]["2"], "estilo": inicial["estilo_preferido"],
              "profundidad": inicial["profundidad_preferida"], "dificultades": [], "tipo": None}]
    for i, mensaje in enumerate(ev["turnos"], 1):
        r = chat(url, mensaje, uid, conv, timeout)
        p = _http(f"{url}/api/v1/perfil/{uid}", None, timeout)
        pasos.append({"turno": i, "mensaje": mensaje, "tipo": r["tipo"], "nivel_u2": p["nivel_por_unidad"]["2"], "estilo": p["estilo_preferido"],
                      "profundidad": p["profundidad_preferida"], "dificultades": [d["tema_id"] for d in p["dificultades"]],
                      "respuesta": r["respuesta"]})
        print(f"[3] turno {i} nivel U2={pasos[-1]['nivel_u2']} estilo={p['estilo_preferido']} dificultades={pasos[-1]['dificultades']}  «{mensaje[:40]}»", flush=True)
    final = chat(url, ev["pregunta_final"], uid, conv + "-nueva", timeout)
    perfil = _http(f"{url}/api/v1/perfil/{uid}", None, timeout)
    progreso = _http(f"{url}/api/v1/perfil/{uid}/progreso", None, timeout)
    tras_reinicio = post_vacio(f"{url}/api/v1/perfil/{uid}/reiniciar", timeout)
    niveles = [p["nivel_u2"] for p in pasos]
    saltos = [round(a - b, 2) for a, b in zip(niveles, niveles[1:])]
    u2 = next(u for u in progreso["unidades"] if u["unidad"] == 2)
    return {
        "usuario": uid, "pasos": pasos, "respuesta_final": final,
        "perfil_final": {"nivel_por_unidad": perfil["nivel_por_unidad"], "estilo": perfil["estilo_preferido"], "profundidad": perfil["profundidad_preferida"],
                         "dificultades": perfil["dificultades"], "historial": perfil["resumen_historial"], "ritmo": perfil["ritmo"]},
        "progreso_unidad_2": [{"nivel": x["nivel"], "motivo": x["motivo"], "tema_id": x["tema_id"]} for x in u2["puntos"]],
        "verdictos": {
            "el_nivel_solo_baja_y_sin_saltos": all(0 <= s <= PASO_MAXIMO + 1e-9 for s in saltos),
            "bajo_al_menos_un_paso": niveles[-1] <= niveles[0] - PASO_MAXIMO + 1e-9,
            "no_entendi_marca_dificultad": bool(pasos[2]["dificultades"]),
            "estilo_pasa_a_ejemplos": pasos[-1]["estilo"] == "ejemplos" and pasos[3]["estilo"] != "ejemplos",
            "progreso_coincide_con_el_nivel": u2["puntos"][-1]["nivel"] == niveles[-1] and u2["nivel_actual"] == niveles[-1],
            "la_siguiente_respuesta_se_adapta": bool(final["adaptacion"]) and final["adaptacion"]["nivel"] == "bajo"
            and final["adaptacion"]["estilo"] == "ejemplos" and final["adaptacion"]["dificultad"],
            "reiniciar_limpia": tras_reinicio["es_nuevo"] and tras_reinicio["nivel_por_unidad"]["2"] == 3.0,
        },
        "saltos": saltos,
    }


# ---------------------------------------------------------------------------------------------- informe

def _celda(texto: str) -> str:
    return texto.replace("|", "\\|").replace("\r", "").replace("\n\n", "<br><br>").replace("\n", "<br>")


def lado_a_lado(textos: dict[str, str], ancho: int = 40) -> str:
    """Las tres respuestas en columnas de texto plano (para leerlas en la terminal)."""
    columnas = {e: textwrap.wrap(" ".join(t.split()), ancho) or [""] for e, t in textos.items()}
    alto = max(len(c) for c in columnas.values())
    encabezado = " │ ".join(e.upper().ljust(ancho) for e in ORDEN)
    filas = [" │ ".join((columnas[e][i] if i < len(columnas[e]) else "").ljust(ancho) for e in ORDEN) for i in range(alto)]
    return "\n".join([encabezado, "─" * len(encabezado), *filas])


def _ok(v: bool) -> str:
    return "✅" if v else "❌"


def escribir_md(informe: dict, ruta: Path) -> None:
    meta = informe["metadatos"]
    out = ["# Evaluación de la adaptación al estudiante", "",
           f"Generado por `pruebas/evaluar_adaptacion.py` el {meta['fecha']} contra `{meta['url']}`"
           + (f" — **{meta['etiqueta']}**" if meta.get("etiqueta") else "") + ".", "",
           "Tres estudiantes con perfiles distintos hacen la misma pregunta. Se espera que las respuestas **difieran en la forma** "
           "(extensión, andamiaje, estilo, cierre) y **coincidan en el contenido normativo**. Los verdictos son heurísticos "
           "(regex y similitud de texto): las respuestas están completas debajo para leerlas.", "",
           "## Estudiantes", "", "| Estudiante | Perfil sembrado |", "|---|---|"]
    for e in ORDEN:
        out.append(f"| **{e}** | {meta['estudiantes'][e]} |")

    out += ["", "## Resumen de verdictos automáticos", "",
            "| Pregunta | Contenido normativo | Forma distinta | Ajustes distintos | Caché por segmento |", "|---|---|---|---|---|"]
    for f in informe["misma_pregunta"]:
        v = f["analisis"]["verdictos"]
        out.append(f"| {f['id']} «{f['pregunta']}» | {_ok(v['contenido_normativo'])} | {_ok(v['forma_distinta'])} | "
                   f"{_ok(v['ajustes_distintos'])} | {_ok(v['cache_por_segmento'])} |")

    for f in informe["misma_pregunta"]:
        a, r = f["analisis"], f["primera"]
        out += ["", f"## {f['id']} · «{f['pregunta']}» (tema {f['tema_id']})", "",
                "| | " + " | ".join(f"**{e}**" for e in ORDEN) + " |", "|---|---|---|---|",
                "| Ajuste aplicado | " + " | ".join(f"`{a['segmentos'][e] or 'ninguno'}`" for e in ORDEN) + " |",
                "| Cita lo ya trabajado | " + " | ".join(", ".join(a["referencias"][e]) or "—" for e in ORDEN) + " |",
                "| Respuesta | " + " | ".join(_celda(r[e]["respuesta"]) for e in ORDEN) + " |",
                "| Palabras | " + " | ".join(str(a["palabras"][e]) for e in ORDEN) + " |",
                "| Normas que nombra | " + " | ".join(", ".join(a["identificadores"][e]) or "—" for e in ORDEN) + " |",
                "| Normas/años sin respaldo en los documentos | " + " | ".join(", ".join(a["no_respaldados"][e]) or "ninguno" for e in ORDEN) + " |",
                "| Ideas ancla que faltan | " + " | ".join(", ".join(a["anclas_que_faltan"][e]) or "ninguna" for e in ORDEN) + " |",
                "| Afirmaciones que los documentos contradicen | " + " | ".join(
                    ", ".join(a["afirmaciones_contradichas"][e]) or "ninguna" for e in ORDEN) + " |",
                "| Marca de analogía/situación | " + " | ".join(_ok(a["marca_analogia"][e]) for e in ORDEN) + " |",
                "", f"Similitud de texto entre pares (1 = idéntico; umbral de «distintas» < {UMBRAL_SIMILITUD}): "
                + ", ".join(f"{k} = {v}" for k, v in a["similitud_entre_pares"].items()) + ". "
                f"El avanzado cierra en pregunta: {_ok(a['cierra_en_pregunta_avanzado'])}; con marca socrática: {_ok(a['marca_socratica_avanzado'])}.", "",
                "**Segunda vez, conversación nueva (caché):** " + ", ".join(
                    f"{k}: {'desde caché' if v else 'generada'}" for k, v in a["cache"].items())
                + f". Recibió lo suyo: {{{', '.join(f'{e}: {_ok(v)}' for e, v in a['recibio_lo_suyo'].items())}}}; "
                f"recibió la respuesta de otro estudiante: {'ninguno' if not any(a['recibio_lo_de_otro'].values()) else a['recibio_lo_de_otro']}; "
                f"el anónimo recibe lo del estándar: {_ok(a['anonimo_recibe_lo_del_estandar'])}."]

    ev = informe["evolucion"]
    if ev:
        out += ["", "## Evolución de un estudiante real", "", informe["metadatos"]["descripcion_evolucion"], "",
                "| Turno | Mensaje | Nivel U2 | Estilo | Profundidad | Temas con dificultad |", "|---|---|---|---|---|---|"]
        for p in ev["pasos"]:
            out.append(f"| {p['turno']} | {p['mensaje']} | {p['nivel_u2']} | {p['estilo']} | {p['profundidad']} | {', '.join(p['dificultades']) or '—'} |")
        fa = ev["respuesta_final"]["adaptacion"] or {}
        out += ["", f"Progreso de la Unidad 2 (`GET /perfil/{{id}}/progreso`): " + " → ".join(
            f"{x['nivel']} ({x['motivo']})" for x in ev["progreso_unidad_2"]) + ".", "",
                f"Al volver a preguntar «{informe['metadatos']['pregunta_final']}» en otra conversación el ajuste fue `{fa.get('segmento')}` "
                f"(nivel {fa.get('nivel')}, estilo {fa.get('estilo')}, dificultad {fa.get('dificultad')}).", "",
                "| Verdicto | |", "|---|---|"]
        for k, v in ev["verdictos"].items():
            out.append(f"| {k.replace('_', ' ')} | {_ok(v)} |")
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text("\n".join(out) + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", default="http://127.0.0.1:8000")
    ap.add_argument("--casos", type=Path, default=RAIZ / "pruebas" / "casos_adaptacion.json")
    ap.add_argument("--perfil-db", type=Path, default=Path(os.environ["PERFIL_DB_PATH"]) if os.environ.get("PERFIL_DB_PATH") else None,
                    help="base de perfiles del servidor (por defecto, PERFIL_DB_PATH)")
    ap.add_argument("--docs", type=Path, default=RAIZ / "documentacion" / "markdown")
    ap.add_argument("--salida-json", type=Path, default=RAIZ / "reportes" / "evaluacion_adaptacion.json")
    ap.add_argument("--salida-md", type=Path, default=RAIZ / "reportes" / "evaluacion_adaptacion.md")
    ap.add_argument("--timeout", type=float, default=600)
    ap.add_argument("--etiqueta", default="")
    ap.add_argument("--sin-evolucion", action="store_true", help="omite la parte 3 (varios turnos, la más lenta)")
    args = ap.parse_args()
    if args.perfil_db is None:
        sys.exit("Falta la base de perfiles: define PERFIL_DB_PATH (la misma que usa el servidor) o pasa --perfil-db.")
    try:
        _http(f"{args.url}/api/v1/documentos", None, 15)
    except Exception as e:
        sys.exit(f"No se pudo contactar con el servidor en {args.url}: {e}")

    casos = json.loads(args.casos.read_text(encoding="utf-8"))
    perfiles, run = PerfilService(args.perfil_db), uuid.uuid4().hex[:8]
    numeros_docs = _numeros_indexados(args.docs)
    misma = parte_misma_pregunta(args.url, perfiles, casos, run, numeros_docs, args.timeout)
    evolucion = None if args.sin_evolucion else parte_evolucion(args.url, casos, run, args.timeout)
    informe = {
        "metadatos": {"fecha": datetime.now().strftime("%Y-%m-%d %H:%M"), "url": args.url, "etiqueta": args.etiqueta, "run": run,
                      "estudiantes": {e: casos["estudiantes"][e]["descripcion"] for e in ORDEN},
                      "descripcion_evolucion": casos["evolucion"]["descripcion"], "pregunta_final": casos["evolucion"]["pregunta_final"]},
        "misma_pregunta": misma, "evolucion": evolucion,
    }
    args.salida_json.parent.mkdir(parents=True, exist_ok=True)
    args.salida_json.write_text(json.dumps(informe, ensure_ascii=False, indent=2), encoding="utf-8")
    escribir_md(informe, args.salida_md)

    for f in misma:
        print(f"\n=== {f['id']} · {f['pregunta']} ===\n" + lado_a_lado({e: f["primera"][e]["respuesta"] for e in ORDEN}))
        print("verdictos:", {k: v for k, v in f["analisis"]["verdictos"].items()})
    if evolucion:
        print("\nevolución:", evolucion["verdictos"])
    print(f"\nEscrito {args.salida_json}\nEscrito {args.salida_md}")


if __name__ == "__main__":
    main()
