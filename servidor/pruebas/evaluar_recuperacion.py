"""Mide la calidad de la recuperación con el banco pruebas/banco_recuperacion.json.

Para cada configuración (modelo de embeddings x recuperación densa | híbrida) indexa documentacion/markdown en un
índice TEMPORAL (no toca base_vectorial/ ni el caché ni la base relacional; no llama al LLM) y, por cada pregunta,
mira los k=4 fragmentos que `RAGService.recuperar` le daría al tutor:
  acierto@1   el primer fragmento es de un documento esperado
  acierto@4   algún fragmento de los 4 es de un documento esperado  (criterio del banco: "entre los primeros")
  fragmentos  cuántos de los 4 son de un documento esperado (sobre 4 x preguntas)
y el mejor score denso (el que decide el filtro de pertinencia).

Uso (desde servidor/):
    python pruebas/evaluar_recuperacion.py                                   # modelo de settings, denso e híbrido
    python pruebas/evaluar_recuperacion.py --modelo sentence-transformers/all-MiniLM-L6-v2 --modelo <otro|carpeta>
Guarda reportes/calidad_recuperacion.json (el análisis está en reportes/calidad_recuperacion.md).
"""
import argparse
import json
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
_TMP = Path(tempfile.mkdtemp(prefix="eval_recuperacion_"))
# Antes de importar app: nada de caché, perfiles ni base relacional reales
os.environ.setdefault("CACHE_ACTIVO", "false")
os.environ.setdefault("PERFIL_ACTIVO", "false")
os.environ["CACHE_DB_PATH"] = str(_TMP / "cache.db")
os.environ["DATABASE_URL"] = f"sqlite:///{(_TMP / 'tutor.db').as_posix()}"
sys.path.insert(0, str(RAIZ / "backend"))

from app.core.config import settings  # noqa: E402
from app.services.rag_service import RAGService  # noqa: E402

CONJUNTOS = ("normas", "variantes", "generales")


def evaluar(rag: RAGService, banco: dict, hibrida: bool, k: int = 4) -> dict:
    settings.RECUPERACION_HIBRIDA = hibrida
    salida = {}
    for conjunto in CONJUNTOS:
        filas = []
        for item in banco[conjunto]:
            rec = rag.recuperar(item["pregunta"], k=k)
            docs = [d.metadata.get("nombre_archivo") for d, _ in rec.resultados]
            esperados = set(item["esperados"])
            filas.append({
                "id": item["id"], "pregunta": item["pregunta"], "esperados": item["esperados"], "recuperados": docs,
                "scores": [round(s, 3) for _, s in rec.resultados], "mejor_densa": round(rec.mejor_densa, 3),
                "acierto_1": bool(docs) and docs[0] in esperados, "acierto_k": any(d in esperados for d in docs),
                "fragmentos_correctos": sum(d in esperados for d in docs)})
        n = len(filas)
        salida[conjunto] = {
            "n": n, "acierto_1": sum(f["acierto_1"] for f in filas), "acierto_k": sum(f["acierto_k"] for f in filas),
            "fragmentos_correctos": sum(f["fragmentos_correctos"] for f in filas), "fragmentos_total": k * n,
            "preguntas": filas}
    return salida


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--modelo", action="append", help="id de Hugging Face o carpeta local (repetible)")
    ap.add_argument("--banco", type=Path, default=RAIZ / "pruebas" / "banco_recuperacion.json")
    ap.add_argument("--salida", type=Path, default=RAIZ / "reportes" / "calidad_recuperacion.json")
    ap.add_argument("--etiqueta", default="")
    args = ap.parse_args()
    banco = json.loads(args.banco.read_text(encoding="utf-8"))
    modelos = args.modelo or [settings.MODELO_EMBEDDINGS]

    # Se acumula sobre una corrida anterior (los modelos se pueden medir por separado)
    informe = json.loads(args.salida.read_text(encoding="utf-8")) if args.salida.exists() else {"configuraciones": {}}
    for modelo in modelos:
        rag = RAGService(persist_dir=_TMP / f"bv_{len(informe['configuraciones'])}_{abs(hash(modelo))}",
                         docs_dir=settings.DOCUMENTACION_DIR, modelo_embeddings=modelo)
        print(f"\n### {modelo}  ({rag.contar_chunks()} fragmentos)")
        for hibrida in (False, True):
            nombre = f"{Path(modelo).name.split('__')[-1]} / {'híbrida' if hibrida else 'densa'}"
            r = evaluar(rag, banco, hibrida)
            informe["configuraciones"][nombre] = {"modelo": modelo, "hibrida": hibrida, **r}
            print(f"  {'híbrida' if hibrida else 'densa  '}:", "   ".join(
                f"{c} @1 {r[c]['acierto_1']}/{r[c]['n']} @4 {r[c]['acierto_k']}/{r[c]['n']} "
                f"frag {r[c]['fragmentos_correctos']}/{r[c]['fragmentos_total']}" for c in CONJUNTOS))
            for f in r["normas"]["preguntas"]:
                if not f["acierto_k"]:
                    print(f"      falla: {f['pregunta']} -> {f['recuperados']} (mejor densa {f['mejor_densa']})")
    informe["generado"] = datetime.now().isoformat(timespec="minutes")
    informe["etiqueta"] = args.etiqueta
    args.salida.write_text(json.dumps(informe, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nGuardado en {args.salida}")


if __name__ == "__main__":
    main()
