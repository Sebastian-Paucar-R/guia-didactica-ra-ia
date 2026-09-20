"""Mide el mejor score (similitud coseno) de cada pregunta contra los documentos reales.

Uso (desde servidor/backend):  python scripts/calibrar_umbral.py
Indexa documentacion/markdown en un store TEMPORAL (no toca base_vectorial/) con los embeddings
reales y no llama al LLM. Sirve para elegir UMBRAL_PERTINENCIA.
"""
import statistics
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.core.config import settings  # noqa: E402
from app.services.rag_service import RAGService  # noqa: E402
from preguntas_pertinencia import DENTRO, FUERA, LIMITE  # noqa: E402


def main():
    # ignore_cleanup_errors: en Windows Chroma mantiene bloqueado el segmento hasta que sale el proceso
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        rag = RAGService(persist_dir=Path(tmp) / "bv", docs_dir=settings.DOCUMENTACION_DIR)
        print(f"\nChunks indexados: {rag.contar_chunks()}\n")
        grupos = {"DENTRO": DENTRO, "FUERA": FUERA, "LIMITE": LIMITE}
        scores: dict[str, list[float]] = {}
        for grupo, preguntas in grupos.items():
            print(f"== {grupo}")
            scores[grupo] = []
            for p in preguntas:
                mejor = max(s for _, s in rag.buscar_con_score(p))
                scores[grupo].append(mejor)
                print(f"  {mejor:.3f}  {p}")
            print()
        for grupo in ("DENTRO", "FUERA"):
            v = scores[grupo]
            print(f"{grupo}: min={min(v):.3f} mediana={statistics.median(v):.3f} max={max(v):.3f}")
        print("\nUmbral -> DENTRO por debajo (confirma LLM) / FUERA por encima (se cuela sin filtro)")
        for u in [x / 100 for x in range(40, 72, 2)]:
            d_bajo = sum(s < u for s in scores["DENTRO"])
            f_alto = sum(s >= u for s in scores["FUERA"])
            print(f"  {u:.2f}: dentro_candidatas={d_bajo}/{len(scores['DENTRO'])}  fuera_que_pasan={f_alto}/{len(scores['FUERA'])}")


if __name__ == "__main__":
    main()
