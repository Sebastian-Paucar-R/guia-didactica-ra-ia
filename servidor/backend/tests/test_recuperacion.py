"""Recuperación híbrida (services/lexico_service.py + RAGService.recuperar) y registro del modelo de embeddings.

Los embeddings son falsos y controlados: la consulta queda densamente más cerca de los documentos de OTRA norma,
que es exactamente el fallo real medido con all-MiniLM-L6-v2 ("¿Qué es ISO/IEC 25010?" traía 29110, 9001 y 27002;
ver reportes/calidad_recuperacion.md)."""
import pytest
from langchain_core.embeddings import Embeddings

from app.core.config import settings
from app.services import lexico_service as lexico
from app.services.rag_service import RAGService
from tests.conftest import texto_largo


class EmbeddingsPorMarca(Embeddings):
    """Vector según qué norma trata el texto; toda consulta cae junto a la 29110 (la equivocada)."""
    VECTORES = {"pequeñas": [1.0, 0.0, 0.0], "gestión de la calidad": [0.9, 0.3, 0.0], "producto": [0.0, 0.0, 1.0]}

    def _vector(self, texto: str) -> list[float]:
        for marca, v in self.VECTORES.items():
            if marca in texto:
                return v
        return [0.0, 1.0, 0.0]

    def embed_documents(self, textos):
        return [self._vector(t) for t in textos]

    def embed_query(self, texto):
        return [1.0, 0.05, 0.0]


DOCUMENTOS = {
    "ISO-IEC_29110_VSE.md": ("# ISO/IEC 29110 — Perfiles para entidades pequeñas\n\n", "entidades pequeñas"),
    "ISO_9001_Calidad.md": ("# ISO 9001 — Sistemas de gestión de la calidad\n\n", "gestión de la calidad"),
    "ISO-IEC_25010_Calidad.md": ("# ISO/IEC 25010 — Modelo de calidad de producto\n\n", "calidad de producto"),
}


@pytest.fixture
def rag_normas(tmp_path, docs, monkeypatch):
    monkeypatch.setattr(settings, "RECUPERACION_HIBRIDA", True)
    (docs / "markdown").mkdir(parents=True)
    for nombre, (titulo, tema) in DOCUMENTOS.items():
        (docs / "markdown" / nombre).write_text(titulo + texto_largo(tema, parrafos=6), encoding="utf-8")
    return RAGService(embeddings=EmbeddingsPorMarca(), persist_dir=tmp_path / "bv", docs_dir=docs)


def _archivos(recuperacion):
    return [d.metadata["nombre_archivo"] for d, _ in recuperacion.resultados]


# ------------------------------------------------------------------------------------------- léxico

def test_tokenizar_quita_tildes_mayusculas_y_palabras_vacias():
    assert lexico.tokenizar("¿Qué es la ISO/IEC 25010 según el Sílabo?") == ["iso", "iec", "25010", "silabo"]


def test_numeros_de_norma_no_toma_decimales_ni_numeros_cortos():
    assert lexico.numeros_de_norma("ISO/IEC 25010:2023, ISO 9001, versión 3.0, 12 puntos") == {"25010", "2023", "9001"}


def test_bm25_prioriza_el_termino_raro():
    bm = lexico.BM25(["calidad del software", "calidad 25010 del producto", "seguridad"])
    p = bm.puntajes("¿qué es 25010?")
    assert p[1] > 0 and p[0] == 0 and p[2] == 0


def test_fusion_rrf_suma_posiciones_y_desempata_por_la_primera_lista():
    # lo que aparece en las dos listas supera al primero de una sola, aunque esté tercero en ella
    assert lexico.fusion_rrf([["a", "b", "c"], ["c", "b"]]) == ["c", "b", "a"]
    assert lexico.fusion_rrf([["a", "b"], ["b", "a"]]) == ["a", "b"]


# ------------------------------------------------------------------------------------------- RAGService.recuperar

def test_densa_sola_reproduce_el_fallo(rag_normas, monkeypatch):
    monkeypatch.setattr(settings, "RECUPERACION_HIBRIDA", False)
    assert "ISO-IEC_25010_Calidad.md" not in _archivos(rag_normas.recuperar("¿Qué es ISO/IEC 25010?"))


def test_hibrida_recupera_la_norma_nombrada(rag_normas):
    rec = rag_normas.recuperar("¿Qué es ISO/IEC 25010?")
    assert _archivos(rec)[0] == "ISO-IEC_25010_Calidad.md"
    assert _archivos(rec).count("ISO-IEC_25010_Calidad.md") >= 3


def test_el_filtro_sigue_viendo_la_mejor_similitud_densa(rag_normas):
    """La fusión saca del contexto a la 29110, pero el score del filtro de pertinencia sigue siendo el suyo."""
    rec = rag_normas.recuperar("¿Qué es ISO/IEC 25010?")
    densa = max(s for _, s in rag_normas.buscar_con_score("¿Qué es ISO/IEC 25010?"))
    assert rec.mejor_densa == pytest.approx(densa)
    assert all(s < rec.mejor_densa for _, s in rec.resultados)   # los de la 25010 son densamente peores


def test_cada_fragmento_lleva_su_similitud_densa(rag_normas):
    for doc, score in rag_normas.recuperar("¿Qué es ISO/IEC 25010?").resultados:
        esperado = max(s for d, s in rag_normas.buscar_con_score("x", k=50) if d.id == doc.id)
        assert score == pytest.approx(esperado)


def test_sin_numero_de_norma_ni_terminos_lexicos_queda_la_densa(rag_normas, monkeypatch):
    pregunta = "¿qué es?"   # todo palabras vacías: ninguna lista léxica
    hibrida = _archivos(rag_normas.recuperar(pregunta))
    monkeypatch.setattr(settings, "RECUPERACION_HIBRIDA", False)
    assert hibrida == _archivos(rag_normas.recuperar(pregunta))


def test_el_filtro_de_leccion_restringe_tambien_la_via_lexica(rag_normas):
    filtro = {"nombre_archivo": {"$in": ["ISO_9001_Calidad.md"]}}
    rec = rag_normas.recuperar("¿Qué es ISO/IEC 25010?", filtro=filtro)
    assert rec.resultados and set(_archivos(rec)) == {"ISO_9001_Calidad.md"}


def test_el_indice_lexico_se_renueva_al_indexar(rag_normas):
    assert "ISO_31000_Riesgo.md" not in _archivos(rag_normas.recuperar("¿Qué es ISO 31000?"))
    nuevo = rag_normas.markdown_dir / "ISO_31000_Riesgo.md"
    nuevo.write_text("# ISO 31000 — Gestión del riesgo\n\n" + texto_largo("riesgo", parrafos=4), encoding="utf-8")
    rag_normas.indexar_archivo(nuevo)
    assert _archivos(rag_normas.recuperar("¿Qué es ISO 31000?"))[0] == "ISO_31000_Riesgo.md"


def test_k_mayor_para_profundizar(rag_normas):
    assert len(rag_normas.recuperar("¿Qué es ISO/IEC 25010?", k=6).resultados) == 6


# ------------------------------------------------------------------------------------------- modelo de embeddings

def test_cambiar_de_modelo_reconstruye_el_indice(tmp_path, docs, capsys):
    (docs / "markdown").mkdir(parents=True)
    (docs / "markdown" / "a.md").write_text(texto_largo("calidad", parrafos=3), encoding="utf-8")
    bv = tmp_path / "bv"
    primero = RAGService(embeddings=EmbeddingsPorMarca(), persist_dir=bv, docs_dir=docs, modelo_embeddings="modelo-a")
    assert {m["modelo_embeddings"] for m in primero.vectorstore.get()["metadatas"]} == {"modelo-a"}

    capsys.readouterr()
    RAGService(embeddings=EmbeddingsPorMarca(), persist_dir=bv, docs_dir=docs, modelo_embeddings="modelo-a")
    assert "otro modelo" not in capsys.readouterr().out    # mismo modelo: nada que reconstruir

    segundo = RAGService(embeddings=EmbeddingsPorMarca(), persist_dir=bv, docs_dir=docs, modelo_embeddings="modelo-b")
    assert "otro modelo" in capsys.readouterr().out
    assert {m["modelo_embeddings"] for m in segundo.vectorstore.get()["metadatas"]} == {"modelo-b"}


def test_embeddings_inyectados_sin_nombre_no_registran_modelo(rag):
    ruta = rag.markdown_dir / "a.md"
    ruta.write_text(texto_largo("calidad", parrafos=2), encoding="utf-8")
    rag.indexar_archivo(ruta)
    assert all("modelo_embeddings" not in m for m in rag.vectorstore.get()["metadatas"])
