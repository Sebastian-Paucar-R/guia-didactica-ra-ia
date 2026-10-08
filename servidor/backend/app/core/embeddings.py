"""Modelo de embeddings del índice vectorial, del caché semántico y de la ubicación en el sílabo.

`crear_embeddings()` es el único lugar que decide qué modelo se usa (`settings.MODELO_EMBEDDINGS`). Cambiarlo
invalida TODO lo calibrado con el anterior: el índice (RAGService.sincronizar lo reconstruye solo al ver chunks de
otro modelo: metadato `modelo_embeddings` de cada chunk), el caché semántico (se vacía con la reconstrucción) y los umbrales
UMBRAL_PERTINENCIA, UMBRAL_RESPALDO y CACHE_UMBRAL_SIMILITUD (recalibrar con scripts/calibrar_umbral.py y
scripts/calibrar_cache.py). Comparativa de modelos: reportes/calidad_recuperacion.md.
"""
from langchain_core.embeddings import Embeddings


class _EmbeddingsConPrefijo(Embeddings):
    """Modelos de la familia E5 (intfloat/multilingual-e5-*): se entrenaron con "query: " delante de la consulta y
    "passage: " delante del texto indexado, y sin esos prefijos su similitud empeora (lo indica su ficha)."""

    def __init__(self, nombre: str, prefijo_consulta: str, prefijo_documento: str):
        from sentence_transformers import SentenceTransformer
        self.modelo = SentenceTransformer(nombre)
        self.prefijo_consulta, self.prefijo_documento = prefijo_consulta, prefijo_documento

    def embed_documents(self, textos: list[str]) -> list[list[float]]:
        return self.modelo.encode([self.prefijo_documento + t for t in textos], normalize_embeddings=True,
                                  batch_size=32).tolist()

    def embed_query(self, texto: str) -> list[float]:
        return self.modelo.encode(self.prefijo_consulta + texto, normalize_embeddings=True).tolist()


def necesita_prefijos(nombre: str) -> bool:
    return "e5" in nombre.lower().replace("\\", "/").split("/")[-1]


def crear_embeddings(nombre: str | None = None) -> Embeddings:
    """`nombre`: id de Hugging Face o carpeta local con el modelo; por defecto `settings.MODELO_EMBEDDINGS`."""
    from app.core.config import settings
    nombre = nombre or settings.MODELO_EMBEDDINGS
    if necesita_prefijos(nombre):
        return _EmbeddingsConPrefijo(nombre, "query: ", "passage: ")
    from langchain_community.embeddings import HuggingFaceEmbeddings
    return HuggingFaceEmbeddings(model_name=nombre)
