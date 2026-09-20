import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.endpoints.documentos import router
from app.core.config import settings
from app.services.rag_service import get_rag_service
from tests.conftest import texto_largo


@pytest.fixture
def client(rag):
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_rag_service] = lambda: rag
    return TestClient(app)


def _archivo(nombre, contenido, campo="archivos"):
    return (campo, (nombre, contenido, "application/octet-stream"))


def test_lote_mixto_no_aborta_por_un_archivo_con_error(client, docs, rag):
    respuesta = client.post("/api/v1/documentos/subir", files=[
        _archivo("bueno.md", texto_largo("calidad").encode()),
        _archivo("malo.exe", b"MZ"),
        _archivo("roto.docx", b"no es un docx"),
        _archivo("vacio.txt", b""),
        _archivo("otro.txt", texto_largo("riesgos").encode()),
    ])
    assert respuesta.status_code == 200
    datos = respuesta.json()
    estados = {r["nombre"]: r["estado"] for r in datos["resultados"]}
    assert estados == {"bueno.md": "indexado", "malo.exe": "error", "roto.docx": "error",
                       "vacio.txt": "error", "otro.txt": "indexado"}
    assert datos["resumen"] == {"total": 5, "indexados": 2, "omitidos_sin_cambios": 0, "errores": 3}

    por_nombre = {r["nombre"]: r for r in datos["resultados"]}
    assert por_nombre["bueno.md"]["rutas"] == {"original": "documentacion/originales/bueno.md",
                                               "pdf": "documentacion/pdf/bueno.pdf",
                                               "markdown": "documentacion/markdown/bueno.md"}
    assert (por_nombre["bueno.md"]["chunks_indexados"] + por_nombre["otro.txt"]["chunks_indexados"]
            == rag.contar_chunks())
    assert all(r["detalle"] for r in datos["resultados"] if r["estado"] == "error")
    # Los rechazados no quedan en originales/ ni dejan carpetas de staging
    assert sorted(p.name for p in (docs / "originales").iterdir()) == ["bueno.md", "otro.txt"]
    assert all(r["rutas"]["original"] is None for r in datos["resultados"] if r["estado"] == "error")
    for carpeta, archivo in (("originales", "bueno.md"), ("pdf", "bueno.pdf"), ("markdown", "bueno.md")):
        assert (docs / carpeta / archivo).is_file()


def test_mismo_nombre_base_en_otro_formato_avisa_del_reemplazo(client, docs, rag):
    client.post("/api/v1/documentos/subir", files=[_archivo("norma.md", texto_largo("uno").encode())])
    r = client.post("/api/v1/documentos/subir", files=[_archivo("norma.txt", texto_largo("dos").encode())]).json()
    resultado = r["resultados"][0]
    assert resultado["estado"] == "indexado" and "norma.md" in resultado["detalle"]
    assert (docs / "originales" / "norma.md").is_file() and (docs / "originales" / "norma.txt").is_file()
    assert {d["nombre_archivo"] for d in rag.resumen_indice()["documentos"]} == {"norma.md"}


def test_upload_corrupto_no_pisa_un_original_valido(client, docs):
    client.post("/api/v1/documentos/subir", files=[_archivo("doc.txt", b"contenido valido")])
    r = client.post("/api/v1/documentos/subir", files=[_archivo("doc.txt", b"\x00\x01binario")]).json()
    assert r["resultados"][0]["estado"] == "error"
    assert (docs / "originales" / "doc.txt").read_bytes() == b"contenido valido"
    assert (docs / "markdown" / "doc.md").read_text(encoding="utf-8") == "contenido valido"


def test_reenviar_el_mismo_archivo_se_omite(client, rag):
    contenido = texto_largo("seguridad").encode()
    client.post("/api/v1/documentos/subir", files=[_archivo("a.md", contenido)])
    total = rag.contar_chunks()
    r = client.post("/api/v1/documentos/subir", files=[_archivo("a.md", contenido)]).json()
    assert r["resultados"][0]["estado"] == "omitido_sin_cambios"
    assert r["resultados"][0]["chunks_indexados"] == 0
    assert rag.contar_chunks() == total


def test_pdf_subido_conserva_el_mismo_archivo_como_copia_pdf(client, docs):
    client.post("/api/v1/documentos/subir", files=[_archivo("base.md", texto_largo("norma").encode())])
    pdf = (docs / "pdf" / "base.pdf").read_bytes()
    r = client.post("/api/v1/documentos/subir", files=[_archivo("copia_pdf.pdf", pdf)]).json()
    assert r["resultados"][0]["estado"] == "indexado", r
    assert (docs / "pdf" / "copia_pdf.pdf").read_bytes() == (docs / "originales" / "copia_pdf.pdf").read_bytes() == pdf


def test_nombre_con_traversal_queda_dentro_de_originales(client, docs, tmp_path):
    r = client.post("/api/v1/documentos/subir",
                    files=[_archivo("../../evil.md", b"# hola\n\ncontenido")]).json()
    assert r["resultados"][0]["estado"] == "indexado"
    assert (docs / "originales" / "evil.md").is_file()
    assert not (tmp_path / "evil.md").exists() and not (tmp_path.parent / "evil.md").exists()


def test_alias_files_y_sin_archivos(client):
    ok = client.post("/api/v1/documentos/subir", files=[_archivo("x.md", b"# x\n\ny", campo="files")])
    assert ok.status_code == 200 and ok.json()["resumen"]["indexados"] == 1
    assert client.post("/api/v1/documentos/subir").status_code == 422


def test_limite_de_tamano(client, monkeypatch):
    monkeypatch.setattr(settings, "MAX_UPLOAD_MB", 0)
    r = client.post("/api/v1/documentos/subir", files=[_archivo("grande.txt", b"x" * 10)]).json()
    assert r["resultados"][0]["estado"] == "error" and "máximo" in r["resultados"][0]["detalle"]


def test_reindexar_y_listado(client, rag):
    client.post("/api/v1/documentos/subir", files=[_archivo("a.md", texto_largo("uno").encode()),
                                                   _archivo("b.md", texto_largo("dos", 4).encode())])
    r = client.post("/api/v1/documentos/reindexar").json()
    assert r["documentos"] == 2 and r["chunks"] == rag.contar_chunks()
    lista = client.get("/api/v1/documentos").json()
    assert lista["total_chunks"] == r["chunks"]
    assert [d["nombre"] for d in lista["documentos"]] == ["a.md", "b.md"]
    assert all(d["indexado"] and d["archivos"]["pdf"] for d in lista["documentos"])
