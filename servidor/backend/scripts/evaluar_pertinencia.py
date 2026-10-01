"""Evalúa el filtro de pertinencia de punta a punta contra el servidor real (con Ollama).

Uso (servidor en marcha, su salida redirigida a un log con PYTHONUTF8=1):
    python scripts/evaluar_pertinencia.py --log ruta/server.log --salida resultados.md [--url http://127.0.0.1:8000]

Por cada pregunta llama a POST /api/v1/chat y cruza la respuesta (campo `tipo`) con la línea
`[FILTRO] ...` que el servidor escribe en su log (score, veredicto del LLM).
"""
import argparse
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from preguntas_pertinencia import DENTRO, FUERA, LIMITE, SOBRE_TUTOR  # noqa: E402

REPETIDA = "¿Cómo preparo una receta de pastel de chocolate?"


def preguntar(url: str, mensaje: str) -> tuple[dict, float]:
    peticion = urllib.request.Request(
        f"{url}/api/v1/chat", data=json.dumps({"mensaje": mensaje}).encode("utf-8"),
        headers={"Content-Type": "application/json"})
    inicio = time.perf_counter()
    with urllib.request.urlopen(peticion, timeout=600) as r:
        return json.load(r), time.perf_counter() - inicio


def leer_nuevas(ruta_log: Path, desde: int) -> tuple[list[str], int]:
    datos = ruta_log.read_bytes()[desde:]
    lineas = [l for l in datos.decode("utf-8", errors="replace").splitlines() if l.startswith("[FILTRO]")]
    return lineas, desde + len(datos)


def resumen_filtro(lineas: list[str]) -> tuple[str, str, str]:
    """(decision, score, veredicto LLM) de la última línea [FILTRO] de la consulta."""
    if not lineas:
        return "-", "-", "-"
    l = lineas[-1]
    decision = re.search(r"decision=(\w+)", l)
    score = re.search(r"score=([\d.\-]+)", l)
    llm = re.search(r"llm=(\w+)", l)
    return (decision.group(1) if decision else "-", score.group(1) if score else "-", llm.group(1) if llm else "-")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:8000")
    ap.add_argument("--log", required=True, type=Path)
    ap.add_argument("--salida", required=True, type=Path)
    args = ap.parse_args()

    posicion = args.log.stat().st_size
    casos = ([("hola", "saludo", "saludo")]
             + [(p, "funcionamiento", "sobre el tutor") for p in SOBRE_TUTOR]
             + [(p, "respuesta", "dentro") for p in DENTRO]
             + [(p, "redireccion", "fuera") for p in FUERA]
             + [(p, None, "límite") for p in LIMITE])
    filas, redirecciones = [], []
    for pregunta, esperado, grupo in casos:
        datos, segundos = preguntar(args.url, pregunta)
        lineas, posicion = leer_nuevas(args.log, posicion)
        decision, score, llm = resumen_filtro(lineas)
        ok = "-" if esperado is None else ("OK" if datos["tipo"] == esperado else "FALLO")
        filas.append((grupo, pregunta, esperado or "(libre)", datos["tipo"], decision, score, llm, ok, segundos))
        if datos["tipo"] == "redireccion":
            redirecciones.append((pregunta, datos["respuesta"]))
        print(f"{ok:5} {grupo:14} {datos['tipo']:15} score={score:6} llm={llm:7} {segundos:5.1f}s  {pregunta}", flush=True)

    # Variación: la misma pregunta fuera de tema, varias veces
    variaciones = []
    for _ in range(3):
        datos, _ = preguntar(args.url, REPETIDA)
        variaciones.append(datos["respuesta"])
        print("VARIACION:", datos["tipo"], flush=True)

    def tasa(grupo):
        f = [x for x in filas if x[0] == grupo]
        return sum(x[7] == "OK" for x in f), len(f)

    out = ["# Resultados de la evaluación (generado por scripts/evaluar_pertinencia.py)\n",
           "| Grupo | Pregunta | Esperado | Obtenido | Decisión | Score | LLM | Resultado | Tiempo |",
           "|---|---|---|---|---|---|---|---|---|"]
    for g, p, e, t, d, s, l, ok, seg in filas:
        out.append(f"| {g} | {p} | {e} | {t} | {d} | {s} | {l} | {ok} | {seg:.1f} s |")
    out.append("\n## Aciertos\n")
    for g in ("saludo", "sobre el tutor", "dentro", "fuera"):
        a, n = tasa(g)
        out.append(f"- {g}: {a}/{n}")
    out.append("\n## Redirecciones generadas\n")
    for p, r in redirecciones:
        out.append(f"**{p}**\n\n> {r.replace(chr(10), chr(10) + '> ')}\n")
    out.append(f"\n## Variación: misma pregunta fuera de tema, 3 veces\n\n**{REPETIDA}**\n")
    for i, r in enumerate(variaciones, 1):
        out.append(f"{i}. > {r.replace(chr(10), ' ')}\n")
    args.salida.write_text("\n".join(out), encoding="utf-8")
    print(f"\nEscrito {args.salida}")


if __name__ == "__main__":
    main()
