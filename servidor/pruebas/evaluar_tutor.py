"""Evalúa el tutor de punta a punta contra el endpoint POST /api/v1/chat con el banco de consultas.

Ejecuta las 60 preguntas de pruebas/banco_consultas.json (40 dentro del temario, 20 fuera) en dos pasadas y
reporta: precisión del filtro de pertinencia, falsos positivos y negativos, latencia media con y sin caché
semántico y cuántas respuestas declararon contexto insuficiente. Guarda reportes/evaluacion_tutor.json y
reportes/evaluacion_tutor.md.

Uso (servidor en marcha; para una medición limpia conviene arrancarlo con un caché vacío, p. ej. con
CACHE_DB_PATH apuntando a un archivo nuevo):
    python pruebas/evaluar_tutor.py [--url http://127.0.0.1:8000] [--etiqueta "texto"] [--robustez]

Definiciones (positivo = "la pregunta es del temario", es decir, el tutor la acepta):
  el filtro ACEPTA una pregunta si la respuesta no es una redirección (tipo != "redireccion");
  verdadero positivo  dentro del temario y aceptada     falso negativo  dentro del temario y redirigida
  verdadero negativo  fuera del temario y redirigida    falso positivo  fuera del temario y aceptada
  Precisión del filtro = (VP + VN) / total. Una respuesta con error (Ollama caído, HTTP) cuenta como fallo.

Pasadas: en la primera se llena el caché; en la segunda repiten las mismas preguntas (cada una en una
conversación nueva) y las respuestas cacheables (tipo respuesta / sin_contexto) salen del caché. La latencia
"sin caché" son las respuestas con desde_cache=false y "con caché" las de desde_cache=true.
"""
import argparse
import json
import re
import statistics
import sys
import time
import urllib.error
import urllib.request
import uuid
from collections import defaultdict
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
CACHEABLES = ("respuesta", "sin_contexto")

# Frases con las que el tutor declara que los documentos no bastan (además del tipo sin_contexto)
_INSUFICIENTE = [re.compile(p, re.IGNORECASE) for p in (
    r"no (?:aparece|aparecen|figura|figuran|se encuentra|se encuentran|est[aá]n?|hay|tengo|cuento|contiene|trata|tratan)\b"
    r"[^.?!]{0,80}\b(?:documentos?|contexto|base|material|fuentes|informaci[oó]n)\b",
    r"\b(?:contexto|documentos|material)\b[^.?!]{0,40}\b(?:no (?:trata|cubre|incluye|menciona|contiene)|es insuficiente|insuficiente)\b",
    r"no (?:est[aá]|aparece|figura) (?:en|dentro de) (?:mis|los|la) (?:documentos|base|documentaci[oó]n)",
    r"no cuento con (?:informaci[oó]n|documentos|material)",
)]


def declara_insuficiente(registro: dict) -> bool:
    return registro["tipo"] == "sin_contexto" or any(p.search(registro["respuesta"]) for p in _INSUFICIENTE)


# ---------------------------------------------------------------------------------------------- HTTP

def _http(url: str, cuerpo: dict | None, timeout: float):
    peticion = urllib.request.Request(
        url, data=json.dumps(cuerpo).encode("utf-8") if cuerpo is not None else None,
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(peticion, timeout=timeout) as r:
        return json.load(r)


def preguntar(url: str, mensaje: str, conversation_id: str, timeout: float) -> dict:
    """Una consulta al chat. Nunca lanza: un fallo de red o del servidor queda como tipo 'error_http'."""
    inicio = time.perf_counter()
    try:
        datos = _http(f"{url}/api/v1/chat", {"mensaje": mensaje, "conversacion_id": conversation_id}, timeout)
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as e:
        datos = {"respuesta": f"{type(e).__name__}: {e}", "tipo": "error_http"}
    espera = (time.perf_counter() - inicio) * 1000
    return {
        "tipo": datos.get("tipo", "error_http"), "respuesta": datos.get("respuesta", ""),
        "desde_cache": bool(datos.get("desde_cache")), "ms_servidor": float(datos.get("latencia_ms") or 0.0),
        "ms_cliente": round(espera, 1), "unidad_obtenida": datos.get("unidad_detectada"),
        "tema_obtenido": datos.get("tema_id_detectado"), "metodo": datos.get("metodo_deteccion"),
        "tiene_campo_ubicacion": datos.get("unidad_detectada") is not None,
    }


# ---------------------------------------------------------------------------------------------- pasadas

def ejecutar_pasada(url: str, preguntas: list[dict], numero: int, timeout: float) -> list[dict]:
    resultados = []
    for i, p in enumerate(preguntas, 1):
        r = preguntar(url, p["pregunta"], f"eval-{uuid.uuid4().hex[:12]}", timeout)
        r.update({"id": p["id"], "pregunta": p["pregunta"], "esperado": p["esperado"], "categoria": p.get("categoria"),
                  "unidad_esperada": p.get("unidad"), "tema_esperado": p.get("tema_id"), "pasada": numero})
        r["aceptada"] = None if r["tipo"] in ("error", "error_http") else r["tipo"] != "redireccion"
        r["acierto"] = r["aceptada"] is not None and r["aceptada"] == (p["esperado"] == "dentro")
        resultados.append(r)
        marca = "OK " if r["acierto"] else "MAL"
        print(f"[pasada {numero}] {i:2}/{len(preguntas)} {marca} {p['id']} esperado={p['esperado']:6} tipo={r['tipo']:12} "
              f"cache={'sí' if r['desde_cache'] else 'no':2} {r['ms_servidor'] / 1000:6.1f}s  {p['pregunta'][:60]}", flush=True)
    return resultados


# ---------------------------------------------------------------------------------------------- métricas

def _pct(a: int, b: int) -> float | None:
    return round(100 * a / b, 1) if b else None


def metricas_filtro(resultados: list[dict]) -> dict:
    vp = [r for r in resultados if r["esperado"] == "dentro" and r["aceptada"] is True]
    fn = [r for r in resultados if r["esperado"] == "dentro" and r["aceptada"] is False]
    vn = [r for r in resultados if r["esperado"] == "fuera" and r["aceptada"] is False]
    fp = [r for r in resultados if r["esperado"] == "fuera" and r["aceptada"] is True]
    errores = [r for r in resultados if r["aceptada"] is None]
    total = len(resultados)
    return {
        "total": total, "aciertos": len(vp) + len(vn),
        "precision_filtro_pct": _pct(len(vp) + len(vn), total),
        "verdaderos_positivos": len(vp), "verdaderos_negativos": len(vn),
        "falsos_positivos": len(fp), "falsos_negativos": len(fn), "errores": len(errores),
        "precision_pct": _pct(len(vp), len(vp) + len(fp)),        # de lo aceptado, cuánto era del temario
        "exhaustividad_pct": _pct(len(vp), len(vp) + len(fn)),    # de lo del temario, cuánto se aceptó
        "especificidad_pct": _pct(len(vn), len(vn) + len(fp)),    # de lo ajeno, cuánto se redirigió
        "lista_falsos_positivos": [{"id": r["id"], "pregunta": r["pregunta"], "tipo": r["tipo"], "respuesta": r["respuesta"][:300]} for r in fp],
        "lista_falsos_negativos": [{"id": r["id"], "pregunta": r["pregunta"], "tipo": r["tipo"], "respuesta": r["respuesta"][:300]} for r in fn],
        "lista_errores": [{"id": r["id"], "pregunta": r["pregunta"], "tipo": r["tipo"], "respuesta": r["respuesta"][:300]} for r in errores],
    }


def _resumen_ms(valores: list[float]) -> dict:
    if not valores:
        return {"n": 0, "media_ms": None, "mediana_ms": None, "p95_ms": None}
    ordenados = sorted(valores)
    return {"n": len(valores), "media_ms": round(statistics.mean(valores), 1), "mediana_ms": round(statistics.median(valores), 1),
            "p95_ms": round(ordenados[min(len(ordenados) - 1, int(0.95 * len(ordenados)))], 1)}


def latencias(todas: list[dict]) -> dict:
    sin = [r for r in todas if not r["desde_cache"] and r["aceptada"] is not None]
    con = [r for r in todas if r["desde_cache"]]
    sin_comparables = [r for r in sin if r["tipo"] in CACHEABLES]
    # Las mismas preguntas: su tiempo en frío (1.ª pasada) frente a su tiempo desde el caché
    frio = {r["id"]: r for r in sin_comparables}
    pares = [(frio[r["id"]]["ms_servidor"], r["ms_servidor"]) for r in con if r["id"] in frio]
    resultado = {
        "sin_cache_todas": _resumen_ms([r["ms_servidor"] for r in sin]),
        "sin_cache_solo_cacheables": _resumen_ms([r["ms_servidor"] for r in sin_comparables]),
        "con_cache": _resumen_ms([r["ms_servidor"] for r in con]),
        "sin_cache_cliente_ms": _resumen_ms([r["ms_cliente"] for r in sin]),
        "con_cache_cliente_ms": _resumen_ms([r["ms_cliente"] for r in con]),
        "mismas_preguntas_en_frio_ms": round(statistics.mean(f for f, _ in pares), 1) if pares else None,
        "mismas_preguntas_con_cache_ms": round(statistics.mean(c for _, c in pares), 1) if pares else None,
    }
    if pares and statistics.mean(c for _, c in pares) > 0:
        resultado["aceleracion_x"] = round(statistics.mean(f for f, _ in pares) / statistics.mean(c for _, c in pares), 1)
    for pasada in sorted({r["pasada"] for r in todas}):
        resultado[f"pasada_{pasada}_todas"] = _resumen_ms([r["ms_servidor"] for r in todas if r["pasada"] == pasada])
    return resultado


def metricas_insuficiente(pasada1: list[dict], cobertura: dict | None) -> dict:
    dentro = [r for r in pasada1 if r["esperado"] == "dentro"]
    por_tipo = [r for r in dentro if r["tipo"] == "sin_contexto"]
    por_texto = [r for r in dentro if r["tipo"] != "sin_contexto" and declara_insuficiente(r)]
    resultado = {
        "preguntas_dentro": len(dentro), "declararon_insuficiente": len(por_tipo) + len(por_texto),
        "por_tipo_sin_contexto": len(por_tipo), "por_texto_en_respuesta": len(por_texto),
        "en_toda_la_evaluacion": sum(declara_insuficiente(r) for r in pasada1),
        "ids": sorted(r["id"] for r in por_tipo + por_texto),
    }
    if cobertura:
        estados = {t["id"]: t["estado"] for t in cobertura["temas"]}
        cruce = defaultdict(lambda: {"preguntas": 0, "declararon_insuficiente": 0})
        for r in dentro:
            e = estados.get(r["tema_esperado"], "desconocido")
            cruce[e]["preguntas"] += 1
            cruce[e]["declararon_insuficiente"] += declara_insuficiente(r)
        resultado["por_cobertura_del_tema"] = dict(cruce)
    return resultado


def metricas_ubicacion(pasada1: list[dict]) -> dict:
    dentro = [r for r in pasada1 if r["esperado"] == "dentro"]
    con_ub = [r for r in dentro if r["unidad_obtenida"] is not None]
    metodos: dict[str, int] = defaultdict(int)
    for r in con_ub:
        metodos[r["metodo"] or "?"] += 1
    return {
        "dentro_con_ubicacion": len(con_ub), "dentro_total": len(dentro),
        "unidad_correcta": sum(r["unidad_obtenida"] == r["unidad_esperada"] for r in con_ub),
        "tema_correcto": sum(r["tema_obtenido"] == r["tema_esperado"] for r in con_ub),
        "unidad_correcta_pct": _pct(sum(r["unidad_obtenida"] == r["unidad_esperada"] for r in con_ub), len(con_ub)),
        "tema_correcto_pct": _pct(sum(r["tema_obtenido"] == r["tema_esperado"] for r in con_ub), len(con_ub)),
        "por_metodo": dict(metodos),
        "fuera_con_ubicacion": [r["id"] for r in pasada1 if r["esperado"] == "fuera" and r["unidad_obtenida"] is not None],
    }


def desglose(pasada1: list[dict], clave: str) -> dict:
    grupos: dict = defaultdict(list)
    for r in pasada1:
        valor = r[clave]
        if valor is not None:
            grupos[valor].append(r)
    return {str(k): {"total": len(v), "aciertos": sum(r["acierto"] for r in v), "pct": _pct(sum(r["acierto"] for r in v), len(v))}
            for k, v in sorted(grupos.items())}


# ---------------------------------------------------------------------------------------------- robustez

_NORMA = re.compile(r"\b(?:ISO|IEC|IEEE)(?:\s*/\s*(?:ISO|IEC|IEEE))*\s*(\d{3,6})(?:\s*:\s*(\d{4}))?", re.IGNORECASE)


def _numeros_indexados(docs_dir: Path) -> set[str]:
    texto = " ".join(p.read_text(encoding="utf-8", errors="replace") for p in docs_dir.glob("*.md"))
    return set(re.findall(r"\d{3,6}", texto))


def _filas_de_tabla(texto: str) -> int:
    return sum(1 for l in texto.splitlines() if l.count("|") >= 3 and not re.fullmatch(r"[\s|:\-]+", l))


def _pasos(texto: str) -> int:
    return len(re.findall(r"(?m)^\s*(?:\*\*)?\d+[.)]\s", texto))


def ejecutar_robustez(url: str, casos: list[dict], docs_dir: Path, timeout: float) -> list[dict]:
    numeros_docs = _numeros_indexados(docs_dir)
    salida = []
    for caso in casos:
        cid = f"eval-rob-{uuid.uuid4().hex[:10]}"
        conversacion, problemas = [], []
        for turno, mensaje in enumerate(caso["turnos"], 1):
            r = preguntar(url, mensaje, cid, timeout)
            conversacion.append({"estudiante": mensaje, "tutor": r["respuesta"], "tipo": r["tipo"], "desde_cache": r["desde_cache"]})
            es_ultimo = turno == len(caso["turnos"])
            if r["tipo"] in ("error", "error_http"):
                problemas.append(f"turno {turno}: error del tutor ({r['tipo']})")
            for patron in caso.get("prohibido_en_ultima", []) if es_ultimo else []:
                if re.search(patron, r["respuesta"], re.IGNORECASE):
                    problemas.append(f"la respuesta contiene «{patron}» (abandonó el rol o filtró sus instrucciones)")
            if es_ultimo and caso.get("requiere_en_ultima") and not all(re.search(p, r["respuesta"], re.IGNORECASE) for p in caso["requiere_en_ultima"]):
                problemas.append("no atendió la parte del temario del mensaje")
            if caso["fallo"] == "norma_inventada":
                validos = numeros_docs | set(re.findall(r"\d{3,6}", mensaje))
                for m in _NORMA.finditer(r["respuesta"]):
                    if m.group(1) not in validos or (m.group(2) and m.group(2) not in validos | set(re.findall(r"\d{4}", mensaje))):
                        problemas.append(f"nombra «{m.group(0)}», que no está en los documentos indexados ni en la pregunta")
            if caso["fallo"] == "insistencia" and turno >= 2:
                if r["tipo"] == "redireccion":
                    problemas.append(f"turno {turno}: redirigió una tarea del temario ya aceptada (no reconoció la insistencia)")
                if "solucion_si_todas_en_turno" in caso and all(re.search(p, r["respuesta"], re.IGNORECASE) for p in caso["solucion_si_todas_en_turno"]):
                    problemas.append(f"turno {turno}: parece entregar la clasificación completa")
                if "solucion_si_pasos_mayor_que" in caso and _pasos(r["respuesta"]) > caso["solucion_si_pasos_mayor_que"]:
                    problemas.append(f"turno {turno}: {_pasos(r['respuesta'])} pasos numerados, parece entregar el plan completo")
                if "solucion_si_filas_de_tabla_mayor_que" in caso and _filas_de_tabla(r["respuesta"]) > caso["solucion_si_filas_de_tabla_mayor_que"]:
                    problemas.append(f"turno {turno}: entrega una tabla con {_filas_de_tabla(r['respuesta'])} filas")
        salida.append({"id": caso["id"], "fallo": caso["fallo"], "aprobado": not problemas, "problemas": problemas, "conversacion": conversacion})
        print(f"[robustez] {caso['id']} {caso['fallo']:16} {'OK' if not problemas else 'FALLA: ' + '; '.join(problemas)}", flush=True)
    return salida


# ---------------------------------------------------------------------------------------------- informe

def _ms(d: dict) -> str:
    return "—" if d["media_ms"] is None else f"{d['media_ms'] / 1000:.2f} s"


def escribir_md(informe: dict, ruta: Path) -> None:
    m, lat, ins, ub = informe["filtro"], informe["latencia"], informe["contexto_insuficiente"], informe["ubicacion"]
    meta = informe["metadatos"]
    out = [
        "# Evaluación del tutor con el banco de consultas", "",
        f"Generado por `pruebas/evaluar_tutor.py` el {meta['fecha']} contra `{meta['url']}`"
        + (f" — **{meta['etiqueta']}**" if meta.get("etiqueta") else "") + ". "
        f"Banco: {meta['preguntas']} consultas ({meta['dentro']} dentro del temario, {meta['fuera']} fuera), {meta['pasadas']} pasadas.", "",
        "## Resultados", "",
        "| Medida | Valor |", "|---|---|",
        f"| **Precisión del filtro** (aciertos / total) | **{m['precision_filtro_pct']} %** ({m['aciertos']}/{m['total']}) |",
        f"| Falsos positivos (fuera del temario, aceptadas) | {m['falsos_positivos']} de {meta['fuera']} |",
        f"| Falsos negativos (dentro del temario, redirigidas) | {m['falsos_negativos']} de {meta['dentro']} |",
        f"| Errores del tutor (cuentan como fallo) | {m['errores']} |",
        f"| Precisión / exhaustividad / especificidad | {m['precision_pct']} % / {m['exhaustividad_pct']} % / {m['especificidad_pct']} % |",
        f"| Latencia media **sin caché** (todas las respuestas) | {_ms(lat['sin_cache_todas'])} (n={lat['sin_cache_todas']['n']}) |",
        f"| Latencia media **sin caché**, solo respuesta/sin_contexto | {_ms(lat['sin_cache_solo_cacheables'])} (n={lat['sin_cache_solo_cacheables']['n']}) |",
        f"| Latencia media **con caché** | {_ms(lat['con_cache'])} (n={lat['con_cache']['n']}) |",
        f"| Mismas preguntas: en frío → desde el caché | {('—' if lat['mismas_preguntas_en_frio_ms'] is None else f'{lat['mismas_preguntas_en_frio_ms'] / 1000:.2f} s → {lat['mismas_preguntas_con_cache_ms'] / 1000:.3f} s ({lat.get('aceleracion_x', '—')}×)')} |",
        f"| Respuestas que declararon contexto insuficiente (preguntas dentro del temario) | {ins['declararon_insuficiente']} de {ins['preguntas_dentro']} "
        f"({ins['por_tipo_sin_contexto']} con tipo `sin_contexto`, {ins['por_texto_en_respuesta']} solo en el texto) |",
        f"| Unidad del sílabo acertada (preguntas dentro con ubicación) | {ub['unidad_correcta_pct']} % ({ub['unidad_correcta']}/{ub['dentro_con_ubicacion']}) |",
        f"| Tema del sílabo acertado | {ub['tema_correcto_pct']} % ({ub['tema_correcto']}/{ub['dentro_con_ubicacion']}) |",
        "",
        "Positivo = «la pregunta es del temario» (el tutor la acepta). Falso positivo: una pregunta ajena que el tutor atendió; "
        "falso negativo: una pregunta del temario que el tutor redirigió. Latencias medidas en el servidor (`tiempo_respuesta_ms`); "
        "las de cliente están en el JSON.", "",
        "## Por unidad y por categoría (aciertos del filtro)", "",
        "| Grupo | Aciertos | % |", "|---|---|---|",
    ]
    for u, d in informe["por_unidad"].items():
        out.append(f"| Unidad {u} | {d['aciertos']}/{d['total']} | {d['pct']} % |")
    for c, d in informe["por_categoria"].items():
        out.append(f"| Fuera: {c} | {d['aciertos']}/{d['total']} | {d['pct']} % |")

    out += ["", "## Cómo se decidió cada consulta del temario", "", "| Método | Consultas |", "|---|---|"]
    for metodo, n in sorted(ub["por_metodo"].items()):
        out.append(f"| {metodo} | {n} |")
    if ub["fuera_con_ubicacion"]:
        out.append(f"\nFuera del temario pero con ubicación asignada (aceptadas): {', '.join(ub['fuera_con_ubicacion'])}")

    if "por_cobertura_del_tema" in ins:
        out += ["", "## Contexto insuficiente según la cobertura del tema", "",
                "| Cobertura del tema (auditoría) | Preguntas | Declararon contexto insuficiente |", "|---|---|---|"]
        for estado, d in sorted(ins["por_cobertura_del_tema"].items()):
            out.append(f"| {estado} | {d['preguntas']} | {d['declararon_insuficiente']} |")

    for titulo, clave in (("Falsos positivos", "lista_falsos_positivos"), ("Falsos negativos", "lista_falsos_negativos"), ("Errores", "lista_errores")):
        if m[clave]:
            out += ["", f"## {titulo}", ""]
            for r in m[clave]:
                out.append(f"- **{r['id']}** «{r['pregunta']}» → `{r['tipo']}`: {r['respuesta'][:200].replace(chr(10), ' ')}")

    out += ["", "## Detalle de la primera pasada", "",
            "| Id | Pregunta | Esperado | Obtenido | Decisión | Método | Unidad (esp./obt.) | Tema (esp./obt.) | Servidor |",
            "|---|---|---|---|---|---|---|---|---|"]
    for r in informe["pasada_1"]:
        decision = "—" if r["aceptada"] is None else ("dentro" if r["aceptada"] else "fuera")
        out.append(f"| {r['id']} | {r['pregunta'][:70].replace('|', '/')} | {r['esperado']} | `{r['tipo']}` | "
                   f"{decision} {'✅' if r['acierto'] else '❌'} | {r['metodo'] or ''} | {r['unidad_esperada'] or ''}/{r['unidad_obtenida'] or ''} | "
                   f"{r['tema_esperado'] or ''}/{r['tema_obtenido'] or ''} | {r['ms_servidor'] / 1000:.1f} s |")

    if informe.get("robustez"):
        rob = informe["robustez"]
        out += ["", "## Robustez del prompt (tres fallos concretos)", "",
                f"Veredictos automáticos (heurísticos): {sum(r['aprobado'] for r in rob)}/{len(rob)} escenarios sin problemas. "
                "Las conversaciones completas están en el JSON para revisarlas a mano.", "",
                "| Escenario | Fallo que se intenta provocar | Resultado |", "|---|---|---|"]
        for r in rob:
            out.append(f"| {r['id']} | {r['fallo']} | {'✅ ok' if r['aprobado'] else '❌ ' + '; '.join(r['problemas'])} |")
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text("\n".join(out) + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", default="http://127.0.0.1:8000")
    ap.add_argument("--banco", type=Path, default=RAIZ / "pruebas" / "banco_consultas.json")
    ap.add_argument("--robustez", action="store_true", help="ejecuta además pruebas/casos_robustez.json")
    ap.add_argument("--casos-robustez", type=Path, default=RAIZ / "pruebas" / "casos_robustez.json")
    ap.add_argument("--cobertura", type=Path, default=RAIZ / "reportes" / "cobertura_silabo.json")
    ap.add_argument("--docs", type=Path, default=RAIZ / "documentacion" / "markdown")
    ap.add_argument("--salida-json", type=Path, default=RAIZ / "reportes" / "evaluacion_tutor.json")
    ap.add_argument("--salida-md", type=Path, default=RAIZ / "reportes" / "evaluacion_tutor.md")
    ap.add_argument("--pasadas", type=int, default=2)
    ap.add_argument("--limite", type=int, help="solo las primeras N preguntas (depuración)")
    ap.add_argument("--timeout", type=float, default=600)
    ap.add_argument("--etiqueta", default="")
    args = ap.parse_args()

    banco = json.loads(args.banco.read_text(encoding="utf-8"))["preguntas"]
    if args.limite:
        banco = banco[:args.limite]
    try:
        _http(f"{args.url}/api/v1/documentos", None, 15)
    except Exception as e:
        sys.exit(f"No se pudo contactar con el servidor en {args.url}: {e}")
    try:
        antes = _http(f"{args.url}/api/v1/cache/estadisticas", None, 15)
        if antes.get("total_entradas"):
            print(f"AVISO: el caché ya tiene {antes['total_entradas']} entradas; la primera pasada puede incluir aciertos.", flush=True)
    except Exception:
        print("AVISO: el caché no responde (desactivado): las latencias 'con caché' quedarán vacías.", flush=True)

    pasadas = [ejecutar_pasada(args.url, banco, n, args.timeout) for n in range(1, args.pasadas + 1)]
    pasada1, todas = pasadas[0], [r for p in pasadas for r in p]
    if not any(r["tiene_campo_ubicacion"] for r in pasada1):
        print("AVISO: las respuestas no traen el campo `ubicacion`: ¿el servidor es anterior al registro de unidad y tema?", flush=True)

    cobertura = json.loads(args.cobertura.read_text(encoding="utf-8")) if args.cobertura.is_file() else None
    informe = {
        "metadatos": {"fecha": datetime.now().strftime("%Y-%m-%d %H:%M"), "url": args.url, "etiqueta": args.etiqueta,
                      "preguntas": len(banco), "dentro": sum(p["esperado"] == "dentro" for p in banco),
                      "fuera": sum(p["esperado"] == "fuera" for p in banco), "pasadas": args.pasadas},
        "filtro": metricas_filtro(pasada1),
        "consistencia_entre_pasadas": (sum(a["aceptada"] != b["aceptada"] for a, b in zip(pasadas[0], pasadas[1]))
                                       if len(pasadas) > 1 else None),
        "latencia": latencias(todas),
        "contexto_insuficiente": metricas_insuficiente(pasada1, cobertura),
        "ubicacion": metricas_ubicacion(pasada1),
        "por_unidad": desglose([r for r in pasada1 if r["esperado"] == "dentro"], "unidad_esperada"),
        "por_categoria": desglose([r for r in pasada1 if r["esperado"] == "fuera"], "categoria"),
        "pasada_1": pasada1,
        "pasada_2": pasadas[1] if len(pasadas) > 1 else [],
    }
    if args.robustez:
        informe["robustez"] = ejecutar_robustez(args.url, json.loads(args.casos_robustez.read_text(encoding="utf-8"))["casos"],
                                                args.docs, args.timeout)
    args.salida_json.parent.mkdir(parents=True, exist_ok=True)
    args.salida_json.write_text(json.dumps(informe, ensure_ascii=False, indent=2), encoding="utf-8")
    escribir_md(informe, args.salida_md)

    m = informe["filtro"]
    print(f"\nPrecisión del filtro: {m['precision_filtro_pct']} % ({m['aciertos']}/{m['total']})  "
          f"FP={m['falsos_positivos']} FN={m['falsos_negativos']} errores={m['errores']}")
    print(f"Escrito {args.salida_json}\nEscrito {args.salida_md}")


if __name__ == "__main__":
    main()
