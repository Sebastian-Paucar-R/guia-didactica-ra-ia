import re
from datetime import datetime

import pytest

from tests.conftest import texto_largo


def _md(rag, nombre, contenido):
    ruta = rag.markdown_dir / nombre
    ruta.write_text(contenido, encoding="utf-8")
    return ruta


def _todo(rag):
    return rag.vectorstore.get(include=["metadatas"])


def test_indexa_documento_nuevo_con_metadata(rag):
    ruta = _md(rag, "iso9001.md", texto_largo("calidad"))
    estado, chunks = rag.indexar_archivo(ruta)
    assert estado == "indexado" and chunks > 1
    datos = _todo(rag)
    assert len(datos["ids"]) == chunks
    for m in datos["metadatas"]:
        assert m["nombre_archivo"] == "iso9001.md"
        assert re.fullmatch(r"[0-9a-f]{64}", m["hash"])
        datetime.fromisoformat(m["fecha_indexado"])


def test_mismo_contenido_se_omite_y_no_duplica(rag):
    ruta = _md(rag, "a.md", texto_largo("riesgos"))
    _, chunks = rag.indexar_archivo(ruta)
    for _ in range(3):
        assert rag.indexar_archivo(ruta) == ("omitido_sin_cambios", 0)
    assert rag.contar_chunks() == chunks


def test_contenido_identico_con_otro_nombre_se_omite(rag):
    rag.indexar_archivo(_md(rag, "a.md", texto_largo("seguridad")))
    antes = rag.contar_chunks()
    assert rag.indexar_archivo(_md(rag, "copia.md", texto_largo("seguridad")))[0] == "omitido_sin_cambios"
    assert rag.contar_chunks() == antes


def test_hash_distinto_reemplaza_chunks_anteriores(rag):
    ruta = _md(rag, "a.md", texto_largo("version uno", parrafos=15))
    rag.indexar_archivo(ruta)
    hash_viejo = _todo(rag)["metadatas"][0]["hash"]

    ruta.write_text(texto_largo("version dos", parrafos=6), encoding="utf-8")
    estado, chunks = rag.indexar_archivo(ruta)

    datos = _todo(rag)
    assert estado == "indexado"
    assert len(datos["ids"]) == chunks == rag.contar_chunks()
    assert hash_viejo not in {m["hash"] for m in datos["metadatas"]}
    assert len(set(datos["ids"])) == len(datos["ids"])


def test_hash_distinto_con_contenido_ya_indexado_retira_version_vieja(rag):
    """a.md pasa a tener el contenido de b.md: no se duplica y se retira lo obsoleto de a.md."""
    a = _md(rag, "a.md", texto_largo("uno"))
    rag.indexar_archivo(a)
    rag.indexar_archivo(_md(rag, "b.md", texto_largo("dos")))
    a.write_text(texto_largo("dos"), encoding="utf-8")
    assert rag.indexar_archivo(a)[0] == "omitido_sin_cambios"
    assert {m["nombre_archivo"] for m in _todo(rag)["metadatas"]} == {"b.md"}


def test_sincronizar_es_idempotente(rag):
    _md(rag, "a.md", texto_largo("uno"))
    _md(rag, "b.md", texto_largo("dos"))
    primero = rag.sincronizar()
    for _ in range(3):
        rag.sincronizar()
    assert rag.contar_chunks() == primero["chunks"]
    assert len(set(_todo(rag)["ids"])) == rag.contar_chunks()


def test_sincronizar_poda_documentos_borrados(rag):
    a = _md(rag, "a.md", texto_largo("uno"))
    _md(rag, "b.md", texto_largo("dos"))
    rag.sincronizar()
    a.unlink()
    rag.sincronizar()
    assert {m["nombre_archivo"] for m in _todo(rag)["metadatas"]} == {"b.md"}


def test_store_con_esquema_anterior_se_reconstruye_sin_duplicados(rag):
    _md(rag, "a.md", texto_largo("uno"))
    # Simula el store antiguo: chunks duplicados, solo con `source`
    rag.vectorstore.add_texts(["viejo"] * 5, metadatas=[{"source": "x.md"}] * 5)
    assert rag.contar_chunks() == 5
    resumen = rag.sincronizar()
    datos = _todo(rag)
    assert all(m.get("hash") for m in datos["metadatas"])
    assert resumen["chunks"] == rag.contar_chunks() == len(datos["ids"])


def test_reconstruir_iguala_la_suma_de_los_documentos(rag):
    _md(rag, "a.md", texto_largo("uno"))
    _md(rag, "b.md", texto_largo("dos", parrafos=4))
    rag.sincronizar()
    resumen = rag.reconstruir()
    assert resumen["documentos"] == 2
    assert resumen["chunks"] == sum(r["chunks"] for r in resumen["resultados"]) == rag.contar_chunks()
    assert rag.retriever.invoke("uno")  # el retriever sigue vivo tras recrear la colección


def test_limpia_segmentos_huerfanos_y_conserva_los_vivos(rag):
    _md(rag, "a.md", texto_largo("uno"))
    rag.sincronizar()
    vivos = {p.name for p in rag.persist_dir.iterdir() if p.is_dir()}
    huerfano = rag.persist_dir / "11111111-2222-3333-4444-555555555555"
    huerfano.mkdir()
    (huerfano / "data_level0.bin").write_bytes(b"x")
    otra = rag.persist_dir / "no-es-un-segmento"
    otra.mkdir()

    rag.sincronizar()  # cada arranque limpia lo que dejó una reconstrucción anterior

    assert not huerfano.exists()
    assert otra.exists(), "solo se tocan carpetas con nombre UUID"
    assert vivos <= {p.name for p in rag.persist_dir.iterdir() if p.is_dir()}
    assert rag.contar_chunks() > 0


def test_documento_vacio_es_error_y_no_indexa(rag):
    with pytest.raises(ValueError):
        rag.indexar_archivo(_md(rag, "vacio.md", "   \n"))
    assert rag.contar_chunks() == 0
