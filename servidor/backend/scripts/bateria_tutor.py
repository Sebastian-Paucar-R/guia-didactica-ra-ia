"""Batería de preguntas para evaluar el prompt del tutor (intención, memoria, citas) contra el servidor real.

Uso (servidor en marcha con PYTHONUTF8=1 y su salida en un log):
    python scripts/bateria_tutor.py --log ruta/server.log --salida resultados_tutor.md [--url http://127.0.0.1:8000]

Cada conversación comparte un conversation_id, así los seguimientos ("explícame eso mejor") prueban la memoria.
La intención detectada sale de la línea `[TUTOR] intencion=...` del log del servidor.
"""
import argparse
import json
import re
import time
import urllib.request
import uuid
from pathlib import Path

# (conversación, mensaje, intención esperada)
BATERIA = [
    ("A", "¿Qué es la mejora continua en la ISO 9001?", "PUNTUAL"),
    ("A", "No entendí muy bien, ¿me lo explicas mejor con un ejemplo?", "PROFUNDIZAR"),
    ("B", "¿Cuál es la diferencia entre ISO/IEC 27001 e ISO/IEC 27002?", "PUNTUAL"),
    ("B", "Amplía eso de los controles, no me quedó claro", "PROFUNDIZAR"),
    ("C", "Resuélveme este ejercicio: identifica los riesgos de mi app móvil de delivery y dame la matriz de "
          "riesgos completa según ISO 31000", "TAREA"),
    ("D", "Redáctame el plan de auditoría interna de calidad de mi proyecto de software, dame todo resuelto", "TAREA"),
    # Extra: contexto insuficiente y riesgo de inventar cláusulas
    ("E", "¿Qué dice la ISO/IEC/IEEE 29119 sobre los niveles de prueba?", "PUNTUAL"),
    ("F", "¿Cuántas cláusulas tiene la ISO 9001 y qué exige la cláusula 8?", "PUNTUAL"),
    ("G", "¿Qué es Scrum y cuáles son sus roles?", "PUNTUAL"),   # tema del sílabo sin documento en la base
]


def preguntar(url: str, mensaje: str, conversation_id: str) -> tuple[dict, float]:
    peticion = urllib.request.Request(
        f"{url}/api/v1/chat",
        data=json.dumps({"mensaje": mensaje, "conversacion_id": conversation_id}).encode("utf-8"),
        headers={"Content-Type": "application/json"})
    inicio = time.perf_counter()
    with urllib.request.urlopen(peticion, timeout=900) as r:
        return json.load(r), time.perf_counter() - inicio


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:8000")
    ap.add_argument("--log", required=True, type=Path)
    ap.add_argument("--salida", required=True, type=Path)
    ap.add_argument("--solo", help="letras de conversación a ejecutar, p. ej. AB")
    args = ap.parse_args()

    ids: dict[str, str] = {}
    posicion = args.log.stat().st_size
    out = ["# Batería del tutor (generado por scripts/bateria_tutor.py)\n"]
    for conv, mensaje, esperada in BATERIA:
        if args.solo and conv not in args.solo:
            continue
        ids.setdefault(conv, uuid.uuid4().hex)
        datos, seg = preguntar(args.url, mensaje, ids[conv])
        nuevo = args.log.read_bytes()[posicion:]
        posicion += len(nuevo)
        lineas = nuevo.decode("utf-8", errors="replace").splitlines()
        intencion = next((m.group(1) for l in lineas if (m := re.search(r"\[TUTOR\] intencion=(\w+)", l))), "-")
        filtro = next((l for l in reversed(lineas) if l.startswith("[FILTRO]")), "")
        reform = next((m.group(1) for l in lineas if (m := re.search(r"reformulada='(.*)'$", l))), "")
        marca = "OK" if intencion == esperada else "REVISAR"
        palabras = len(datos["respuesta"].split())
        print(f"[{conv}] {marca:7} esperada={esperada:11} detectada={intencion:11} tipo={datos['tipo']:10} "
              f"{palabras:4} palabras {seg:5.1f}s | {mensaje[:70]}", flush=True)
        out += [f"## [{conv}] {mensaje}\n",
                f"- Intención esperada: **{esperada}**, detectada: **{intencion}** ({marca})",
                f"- tipo: `{datos['tipo']}` · {palabras} palabras · {seg:.1f} s",
                f"- Pregunta reescrita por la memoria: {reform or '(sin cambios)'}",
                f"- Filtro: `{filtro or '-'}`\n",
                "> " + datos["respuesta"].replace("\n", "\n> "), ""]
    args.salida.write_text("\n".join(out), encoding="utf-8")
    print(f"\nEscrito {args.salida}")


if __name__ == "__main__":
    main()
