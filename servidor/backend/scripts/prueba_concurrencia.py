"""Mide el comportamiento de la cola de generación (app/services/cola_service.py) con N peticiones a /api/v1/chat
simultáneas, contra el RAG y el LLM REALES (Ollama debe estar corriendo) — sin necesitar credenciales reales de
Firebase: se sustituye `usuario_actual` por un estudiante de prueba ya consentido, en proceso (httpx contra la
app ASGI directamente, sin abrir un socket), igual que hacen los tests de este proyecto.

Uso (desde servidor/backend/, con Ollama corriendo y el modelo de MODELO_LLM ya descargado):
    python ../scripts/prueba_concurrencia.py [--niveles 10,20,40] [--repeticiones 1]

Escribe reportes/prueba_concurrencia.md y reportes/prueba_concurrencia.json. El límite de generaciones
simultáneas que se mide es el configurado en LIMITE_GENERACIONES_SIMULTANEAS (.env o variable de entorno) en el
momento de arrancar este script — no un flag propio, para medir la configuración real, no una simulada.
"""
import argparse
import asyncio
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]      # servidor/backend/
RAIZ = BACKEND_DIR.parent                               # servidor/ (donde vive reportes/)
sys.path.insert(0, str(BACKEND_DIR))

import httpx  # noqa: E402

from app.api.deps import usuario_actual  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.db.models import Usuario  # noqa: E402
from app.main import app  # noqa: E402

PREGUNTAS = [
    "¿Qué fases tiene el ciclo de vida del desarrollo de software?",
    "¿Para qué sirve la norma ISO 9001 y qué es un sistema de gestión de la calidad?",
    "¿Qué es ISO/IEC 25010 y qué características de calidad define?",
    "¿Cuál es la diferencia entre certificación y acreditación de una organización?",
    "¿Cómo se estima el esfuerzo de un proyecto de software usando puntos de función?",
    "¿Qué diferencia hay entre lead time y cycle time?",
    "¿Cuál es la diferencia entre pruebas unitarias, de integración y de aceptación?",
    "¿Qué establece la ISO/IEC/IEEE 29119 sobre las pruebas de software?",
    "¿Cómo funciona un tablero Kanban y por qué se limita el trabajo en progreso?",
    "¿En qué consiste la cultura DevOps y qué añade DevSecOps?",
]


def _usuario_de_prueba() -> Usuario:
    ahora = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return Usuario(uid_firebase="carga-prueba", correo="carga@prueba.local", nombre="Carga de prueba",
                  foto_url=None, proveedor="password", rol="estudiante", fecha_registro=ahora,
                  ultimo_acceso=ahora, consentimiento_aceptado=True, consentimiento_fecha=ahora)


app.dependency_overrides[usuario_actual] = _usuario_de_prueba


async def _disparar(cliente: httpx.AsyncClient, i: int, pregunta: str) -> dict:
    t0 = time.perf_counter()
    try:
        r = await cliente.post("/api/v1/chat", json={"mensaje": pregunta, "conversacion_id": f"carga-{i}-{t0}"})
        ms_cliente = (time.perf_counter() - t0) * 1000
        d = r.json()
        return {"i": i, "status": r.status_code, "ms_cliente": round(ms_cliente, 1),
                "tiempo_respuesta_ms": d.get("latencia_ms"), "tipo": d.get("tipo"),
                "desde_cache": d.get("desde_cache"), "posicion_en_cola": d.get("posicion_en_cola"),
                "espera_estimada_s": d.get("espera_estimada_s"), "espera_real_s": d.get("espera_real_s")}
    except Exception as e:
        ms_cliente = (time.perf_counter() - t0) * 1000
        return {"i": i, "status": None, "ms_cliente": round(ms_cliente, 1), "error": f"{type(e).__name__}: {e}"}


async def _nivel(n: int) -> tuple[list[dict], float]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://prueba-concurrencia", timeout=300) as cliente:
        preguntas = [PREGUNTAS[i % len(PREGUNTAS)] for i in range(n)]
        t0 = time.perf_counter()
        resultados = await asyncio.gather(*[_disparar(cliente, i, preguntas[i]) for i in range(n)])
        total_s = time.perf_counter() - t0
    return resultados, total_s


def _resumen(valores: list[float]) -> dict:
    if not valores:
        return {"n": 0}
    ordenados = sorted(valores)
    return {"n": len(valores), "media_ms": round(statistics.mean(valores), 1),
            "mediana_ms": round(statistics.median(valores), 1),
            "p95_ms": round(ordenados[min(len(ordenados) - 1, int(0.95 * len(ordenados)))], 1),
            "max_ms": round(max(valores), 1), "min_ms": round(min(valores), 1)}


def _analizar(n: int, resultados: list[dict], total_s: float) -> dict:
    ok = [r for r in resultados if r.get("status") == 200]
    errores = [r for r in resultados if r.get("status") != 200]
    con_espera = [r for r in ok if r.get("posicion_en_cola") is not None]
    return {
        "n_peticiones": n,
        "limite_generaciones_simultaneas": settings.LIMITE_GENERACIONES_SIMULTANEAS,
        "espera_maxima_s": settings.ESPERA_MAXIMA_COLA_S,
        "duracion_total_s": round(total_s, 2),
        "ok": len(ok), "errores": len(errores),
        "detalle_errores": [{"i": r["i"], "status": r.get("status"), "error": r.get("error"),
                             "tipo": r.get("tipo")} for r in errores][:10],
        "latencia_servidor_ms": _resumen([r["tiempo_respuesta_ms"] for r in ok if r.get("tiempo_respuesta_ms") is not None]),
        "latencia_cliente_ms": _resumen([r["ms_cliente"] for r in ok]),
        "peticiones_que_esperaron_cupo": len(con_espera),
        "espera_en_cola_s": _resumen([r["espera_real_s"] * 1000 for r in con_espera]) if con_espera else {"n": 0},
        "posicion_maxima_al_llegar": max((r["posicion_en_cola"] for r in con_espera), default=0),
        "throughput_peticiones_por_s": round(len(ok) / total_s, 2) if total_s > 0 else None,
    }


def _escribir_md(analisis: list[dict], ruta: Path) -> None:
    out = ["# Prueba de concurrencia de la cola de generación", "",
          f"Generado el {datetime.now().strftime('%Y-%m-%d %H:%M')} contra el RAG y el LLM reales "
          f"(`MODELO_LLM={settings.MODELO_LLM}`), en proceso (sin red, sin credenciales de Firebase: "
          "`usuario_actual` sustituido por un estudiante de prueba ya consentido). Cada nivel dispara N peticiones "
          "a `/api/v1/chat` EXACTAMENTE a la vez (`asyncio.gather`), cada una con su propia `conversation_id` y una "
          "pregunta real distinta (rotando un banco de 10), para no confundir la cola con aciertos de caché.", "",
          f"**Límite de generaciones simultáneas probado: `LIMITE_GENERACIONES_SIMULTANEAS = "
          f"{settings.LIMITE_GENERACIONES_SIMULTANEAS}`** (espera máxima: {settings.ESPERA_MAXIMA_COLA_S:.0f} s).", "",
          "## Resultados", "",
          "| Peticiones | Errores | Duración total | Latencia servidor (media / p95) | Esperaron cupo | Posición máx. al llegar | Rendimiento |",
          "|---|---|---|---|---|---|---|"]
    for a in analisis:
        lat = a["latencia_servidor_ms"]
        media = f"{lat['media_ms'] / 1000:.2f} s" if lat.get("n") else "—"
        p95 = f"{lat['p95_ms'] / 1000:.2f} s" if lat.get("n") else "—"
        out.append(f"| {a['n_peticiones']} | {a['errores']} | {a['duracion_total_s']:.2f} s | {media} / {p95} | "
                   f"{a['peticiones_que_esperaron_cupo']} de {a['ok']} | {a['posicion_maxima_al_llegar']} | "
                   f"{a['throughput_peticiones_por_s']} peticiones/s |")
    out += ["", "Positivo = petición resuelta con HTTP 200 (incluye respuestas, redirecciones, sin_contexto...: "
           "cualquier turno que el servidor completó). \"Esperaron cupo\" = la respuesta trajo `cola` (la petición "
           "encontró los cupos ocupados a su llegada). \"Posición máx. al llegar\" = el peor caso observado de "
           "cuántas peticiones ya esperaban cuando otra se puso en cola.", ""]
    for a in analisis:
        out += [f"## {a['n_peticiones']} peticiones simultáneas", "",
               f"- Duración total del lote: **{a['duracion_total_s']:.2f} s** "
               f"({a['throughput_peticiones_por_s']} peticiones/s de media).",
               f"- {a['ok']} de {a['n_peticiones']} resueltas con HTTP 200"
               + (f"; **{a['errores']} con error** (ver detalle abajo)." if a['errores'] else ", sin errores."),
               f"- Latencia del servidor (`tiempo_respuesta_ms`): media {a['latencia_servidor_ms'].get('media_ms', '—')} ms, "
               f"mediana {a['latencia_servidor_ms'].get('mediana_ms', '—')} ms, "
               f"p95 {a['latencia_servidor_ms'].get('p95_ms', '—')} ms, "
               f"máxima {a['latencia_servidor_ms'].get('max_ms', '—')} ms.",
               f"- {a['peticiones_que_esperaron_cupo']} peticiones encontraron la cola ocupada a su llegada "
               f"(de {a['ok']} resueltas); posición máxima observada al llegar: {a['posicion_maxima_al_llegar']}."]
        if a["espera_en_cola_s"].get("n"):
            e = a["espera_en_cola_s"]
            out.append(f"- De las que esperaron: espera media {e['media_ms'] / 1000:.2f} s, "
                      f"máxima {e['max_ms'] / 1000:.2f} s.")
        if a["detalle_errores"]:
            out += ["", "  Errores:"] + [f"  - #{e['i']}: status={e['status']} tipo={e.get('tipo')} {e.get('error') or ''}"
                                         for e in a["detalle_errores"]]
        out.append("")
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text("\n".join(out) + "\n", encoding="utf-8")


async def _todos_los_niveles(niveles: list[int]) -> list[dict]:
    """Un solo event loop para todos los niveles: `cola` (services/cola_service.py) es un singleton de módulo
    con un asyncio.Semaphore/asyncio.Lock, que se ata al primer event loop en el que se usa. Correr cada nivel
    con su propio `asyncio.run()` (un loop nuevo cada vez) rompe esos objetos con "is bound to a different
    event loop" a partir del segundo nivel — un problema del propio guion de prueba, no del servidor real: un
    proceso de uvicorn corre un único event loop durante toda su vida, así que esto nunca pasa en producción."""
    analisis = []
    for n in niveles:
        print(f"\n=== {n} peticiones simultáneas ===", flush=True)
        resultados, total_s = await _nivel(n)
        a = _analizar(n, resultados, total_s)
        analisis.append(a)
        print(f"  {a['ok']}/{n} OK, {a['errores']} errores, {a['duracion_total_s']} s total, "
             f"{a['peticiones_que_esperaron_cupo']} esperaron cupo (máx. posición {a['posicion_maxima_al_llegar']})",
             flush=True)
    return analisis


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--niveles", default="10,20,40", help="niveles de concurrencia separados por coma")
    ap.add_argument("--salida-json", type=Path, default=RAIZ / "reportes" / "prueba_concurrencia.json")
    ap.add_argument("--salida-md", type=Path, default=RAIZ / "reportes" / "prueba_concurrencia.md")
    args = ap.parse_args()
    niveles = [int(n) for n in args.niveles.split(",")]

    print(f"LIMITE_GENERACIONES_SIMULTANEAS={settings.LIMITE_GENERACIONES_SIMULTANEAS}  "
         f"ESPERA_MAXIMA_COLA_S={settings.ESPERA_MAXIMA_COLA_S}  MODELO_LLM={settings.MODELO_LLM}")

    analisis = asyncio.run(_todos_los_niveles(niveles))

    import json
    args.salida_json.parent.mkdir(parents=True, exist_ok=True)
    args.salida_json.write_text(json.dumps(analisis, ensure_ascii=False, indent=2), encoding="utf-8")
    _escribir_md(analisis, args.salida_md)
    print(f"\nEscrito {args.salida_json}\nEscrito {args.salida_md}")


if __name__ == "__main__":
    main()
