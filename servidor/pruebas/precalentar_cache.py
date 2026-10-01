"""Precalienta el caché semántico de respuestas con las preguntas frecuentes de configuracion/preguntas_frecuentes.json,
antes de una sesión con estudiantes: las consultas más probables responden desde caché en milisegundos
(ver services/cache_service.py) en vez de esperar 2-40 s a que el LLM genere de verdad la primera vez.

Corre en proceso, sin pasar por HTTP (no hace falta token de Firebase: no es una petición de un estudiante, es
mantenimiento) — instancia el mismo RAGService que usaría el servidor, contra la base vectorial y el caché
REALES (BASE_VECTORIAL_DIR / CACHE_DB_PATH de core/config.py; usa las variables de entorno para apuntar a otros
si se quiere precalentar sin tocar los reales, igual que pruebas/evaluar_tutor.py).

Cada pregunta se guarda con el ajuste NEUTRO (sin `user_id`): es el que comparten los estudiantes anónimos y los
que todavía no tienen perfil (ver adaptacion_service.py, "Invariante del caché"), así que es el que más aciertos
va a dar. Un estudiante con perfil no neutro (nivel fuera de la franja media, profundidad o estilo no
"conceptual"/"media") seguirá generando su propia respuesta la primera vez — precalentar para cada combinación
posible de perfil no es práctico ni necesario: solo unos pocos estudiantes llegan con un perfil tan marcado antes
de haber hecho ninguna pregunta.

Uso (desde servidor/backend/, con el mismo Python que corre el servidor):
    python ../pruebas/precalentar_cache.py [--preguntas ruta.json] [--limite N]
"""
import argparse
import json
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "backend"))

from app.services.rag_service import RAGService  # noqa: E402


def cargar_preguntas(ruta: Path) -> list[tuple[int, str]]:
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    return [(u["unidad"], p) for u in datos["unidades"] for p in u["preguntas"]]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--preguntas", type=Path, default=RAIZ / "configuracion" / "preguntas_frecuentes.json")
    ap.add_argument("--limite", type=int, help="solo las primeras N preguntas (para probar rápido)")
    args = ap.parse_args()

    preguntas = cargar_preguntas(args.preguntas)
    if args.limite:
        preguntas = preguntas[:args.limite]
    if not preguntas:
        sys.exit(f"{args.preguntas} no tiene preguntas.")

    print(f"Precalentando {len(preguntas)} preguntas de {args.preguntas} ...")
    rag = RAGService()   # settings reales: BASE_VECTORIAL_DIR / CACHE_DB_PATH / MODELO_LLM de siempre
    if rag.cache is None:
        sys.exit("El caché semántico está apagado (CACHE_ACTIVO=false): no hay nada que precalentar.")

    nuevas = reutilizadas = 0
    for i, (unidad, pregunta) in enumerate(preguntas, 1):
        t0 = time.perf_counter()
        r = rag.get_answer(pregunta)
        ms = (time.perf_counter() - t0) * 1000
        estado = "ya en caché" if r.get("desde_cache") else "generada y guardada"
        if r.get("desde_cache"):
            reutilizadas += 1
        elif r["tipo"] in ("respuesta", "sin_contexto"):
            nuevas += 1
        print(f"[{i:2}/{len(preguntas)}] U{unidad} {estado:20} {ms:7.0f} ms  tipo={r['tipo']:12} {pregunta[:60]}")

    print(f"\nListo: {nuevas} respuestas nuevas guardadas, {reutilizadas} ya estaban en caché "
          f"(de {len(preguntas)} preguntas).")


if __name__ == "__main__":
    main()
