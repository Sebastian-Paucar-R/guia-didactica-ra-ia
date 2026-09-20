"""Caché semántico de respuestas: SQLite persistente, umbral, salvaguardas, invalidación y estadísticas.

Los embeddings son controlados (cada pregunta tiene un vector con la similitud deseada respecto a otra) y los
LLMs falsos cuentan sus llamadas, así que se comprueba que un acierto no llama al LLM.
"""
import sqlite3
import time
from types import SimpleNamespace

import numpy as np
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from langchain_core.embeddings import DeterministicFakeEmbedding, Embeddings

import app.services.rag_service as rag_module
from app.api.v1.endpoints.cache import router as cache_router
from app.api.v1.endpoints.documentos import router as documentos_router
from app.core.config import settings
from app.services import tutor_service as tutor
from app.services.cache_service import CacheSemantico, huella_de, intencion_de
from app.services.rag_service import RAGService, get_rag_service
from tests.conftest import LLMFalso, texto_largo

DIM = 8
Q1 = "¿Qué es la calidad del software?"
Q2 = "Dime en qué consiste la calidad del software"
Q3 = "¿Cuáles son las características de la calidad del software?"


def vec(similitud: float) -> np.ndarray:
    """Vector unitario con esa similitud coseno respecto a vec(1.0)."""
    v = np.zeros(DIM)
    v[0], v[1] = similitud, np.sqrt(max(1 - similitud ** 2, 0.0))
    return v


class EmbeddingsControlados(Embeddings):
    """Vectores fijos para las preguntas que interesan; el resto, deterministas (indexado de documentos)."""

    def __init__(self):
        self.base = DeterministicFakeEmbedding(size=DIM)
        self.fijos: dict[str, list[float]] = {}

    def embed_documents(self, textos):
        return self.base.embed_documents(textos)

    def embed_query(self, texto):
        return list(self.fijos[texto]) if texto in self.fijos else self.base.embed_query(texto)


class LLMConEfecto(LLMFalso):
    """LLMFalso que ejecuta `efecto()` en cada llamada (simula una generación lenta o un cambio concurrente)."""

    def __init__(self, respuesta, efecto=None):
        super().__init__(respuesta)
        self.efecto = efecto

    def __call__(self, valor_prompt):
        if self.efecto:
            self.efecto()
        return super().__call__(valor_prompt)


def _filas(cache, sql, *args):
    con = sqlite3.connect(cache.ruta)
    try:
        return con.execute(sql, args).fetchall()
    finally:
        con.close()


def _entradas(cache) -> int:
    return _filas(cache, "SELECT COUNT(*) FROM respuestas")[0][0]


# ================================================================ CacheSemantico (unitarios)

@pytest.fixture
def cache(tmp_path):
    return CacheSemantico(tmp_path / "cache_respuestas.db", umbral=0.92)


def _guardar(cache, pregunta="¿Qué es ISO 25010?", similitud=1.0, respuesta="R", ms=1000.0, vector=None):
    return cache.guardar(pregunta, vec(similitud) if vector is None else vector, respuesta, "contexto",
                         ["iso_25010.md"], "respuesta", ms, cache.version())


def base(i: int, dim: int = 16) -> np.ndarray:
    """Vector i-ésimo de la base canónica: preguntas con embeddings ortogonales (similitud 0 entre sí)."""
    v = np.zeros(dim)
    v[i] = 1.0
    return v


def test_acierto_solo_si_la_similitud_llega_al_umbral(cache):
    assert _guardar(cache)
    a = cache.buscar("¿Qué es ISO 25010?", vec(0.93))
    assert a is not None and a.respuesta == "R" and a.fuentes == ["iso_25010.md"] and a.contexto == "contexto"
    assert a.similitud == pytest.approx(0.93)
    assert cache.buscar("¿Qué es ISO 25010?", vec(0.91)) is None


def test_el_umbral_es_configurable(cache):
    _guardar(cache)
    assert cache.buscar("¿Qué es ISO 25010?", vec(0.90)) is None
    laxo = CacheSemantico(cache.ruta, umbral=0.85)
    assert laxo.buscar("¿Qué es ISO 25010?", vec(0.90)) is not None


def test_sobrevive_al_reinicio(cache):
    _guardar(cache)
    reabierto = CacheSemantico(cache.ruta, umbral=0.92)      # "servidor nuevo" sobre el mismo archivo
    assert reabierto.buscar("¿Qué es ISO 25010?", vec(1.0)).respuesta == "R"
    assert reabierto.estadisticas()["total_entradas"] == 1


def test_embedding_de_otra_dimension_no_rompe_ni_acierta(cache):
    _guardar(cache)
    assert cache.buscar("¿Qué es ISO 25010?", [1.0, 0.0, 0.0, 0.0]) is None


def test_registrar_acierto_incrementa_el_contador_y_la_fecha(cache):
    _guardar(cache)
    antes = _filas(cache, "SELECT usos, creado_en, ultimo_uso FROM respuestas")[0]
    assert antes[0] == 0 and antes[1] == antes[2]
    time.sleep(1.1)   # las fechas tienen resolución de segundos
    for _ in range(2):
        cache.registrar_acierto(cache.buscar("¿Qué es ISO 25010?", vec(1.0)), 10.0)
    usos, creado, ultimo = _filas(cache, "SELECT usos, creado_en, ultimo_uso FROM respuestas")[0]
    assert usos == 2 and ultimo > creado


def test_intencion_distinta_no_comparte_respuesta(cache):
    _guardar(cache, "¿Qué es ISO 25010?")
    assert intencion_de("¿Qué es ISO 25010?") == tutor.PUNTUAL
    assert intencion_de("Resuélveme el ejercicio de ISO 25010") == tutor.TAREA
    assert intencion_de("Dame un ejemplo de ISO 25010") == tutor.PROFUNDIZAR
    assert cache.buscar("Resuélveme el ejercicio de ISO 25010", vec(0.99)) is None
    assert cache.buscar("Dame un ejemplo de ISO 25010", vec(0.99)) is None


@pytest.mark.parametrize("guardada, nueva", [
    ("¿Qué es la norma ISO 9001?", "¿Qué es la norma ISO 27001?"),          # 0.90 con MiniLM real
    ("¿Qué es ISO 25010?", "¿Qué no es ISO 25010?"),                         # 0.974 con MiniLM real
    ("¿Qué es CMMI?", "¿Qué es SPICE?"),
    ("Requisitos de ISO 9001:2015", "Requisitos de ISO 9001"),
])
def test_preguntas_casi_iguales_para_el_modelo_pero_distintas_no_se_confunden(cache, guardada, nueva):
    _guardar(cache, guardada)
    assert cache.buscar(guardada, vec(1.0)) is not None
    assert cache.buscar(nueva, vec(0.99)) is None


def test_la_huella_ignora_iso_iec_ieee_y_mayusculas_de_estilo():
    assert huella_de("¿Qué es ISO 25010?") == huella_de("Explícame la norma ISO/IEC 25010, por favor")
    assert huella_de("qué es iso 25010") == huella_de("¿Qué es la norma ISO/IEC/IEEE 25010?")


def test_invalidar_vacia_todo_y_la_version_rechaza_lo_generado_antes(cache):
    version = cache.version()
    assert _guardar(cache) and _guardar(cache, "¿Qué es ISO 9001?")
    assert cache.invalidar("prueba") == 2
    assert _entradas(cache) == 0 and cache.version() == version + 1
    # una respuesta generada con la versión anterior no entra
    assert not cache.guardar("¿Qué es ISO 25010?", vec(1.0), "vieja", "", [], "respuesta", 5.0, version)
    assert _entradas(cache) == 0
    assert cache.guardar("¿Qué es ISO 25010?", vec(1.0), "nueva", "", [], "respuesta", 5.0, cache.version())


def test_estadisticas_sin_datos_no_dividen_por_cero(cache):
    e = cache.estadisticas()
    assert e["total_entradas"] == 0 and e["tasa_aciertos"] == 0.0 and e["tiempo_promedio_ahorrado_ms"] == 0.0
    assert e["preguntas_mas_repetidas"] == [] and e["invalidaciones"] == 0 and e["ultima_invalidacion"] is None


def test_estadisticas_tasa_repetidas_y_tiempo_ahorrado(cache):
    for i, nombre in enumerate(("¿Qué es A?", "¿Qué es B?", "¿Qué es C?")):
        _guardar(cache, nombre, ms=1000.0, vector=base(i))
        cache.registrar_fallo()
    a, b = (cache.buscar(n, base(i)) for i, n in enumerate(("¿Qué es A?", "¿Qué es B?")))
    for hit, veces in ((a, 3), (b, 1)):
        for _ in range(veces):
            cache.registrar_acierto(hit, 10.0)
    e = cache.estadisticas()
    assert (e["total_entradas"], e["aciertos"], e["fallos"], e["consultas"]) == (3, 4, 3, 7)
    assert e["tasa_aciertos"] == pytest.approx(4 / 7, abs=1e-4)
    assert [(p["pregunta"], p["usos"]) for p in e["preguntas_mas_repetidas"]] == [("¿Qué es A?", 3), ("¿Qué es B?", 1)]
    assert e["tiempo_promedio_ahorrado_ms"] == 990.0 and e["tiempo_total_ahorrado_ms"] == 3960.0
    assert e["umbral_similitud"] == 0.92


def test_estadisticas_devuelve_como_maximo_diez_y_conserva_contadores_tras_invalidar(cache):
    for i in range(12):
        _guardar(cache, f"¿Qué es el concepto {'x' * i}?", vector=base(i))
        hit = cache.buscar(f"¿Qué es el concepto {'x' * i}?", base(i))
        cache.registrar_acierto(hit, 1.0)
    assert len(cache.estadisticas()["preguntas_mas_repetidas"]) == 10
    cache.invalidar("cambio en los documentos")
    e = cache.estadisticas()
    assert e["total_entradas"] == 0 and e["preguntas_mas_repetidas"] == []
    assert e["aciertos"] == 12 and e["invalidaciones"] == 1 and e["motivo_ultima_invalidacion"] == "cambio en los documentos"


# ================================================================ integración con RAGService

@pytest.fixture
def rig(tmp_path, docs, monkeypatch):
    monkeypatch.setattr(settings, "UMBRAL_PERTINENCIA", -1.0)   # todo pertinente: aquí se prueba el caché
    (docs / "markdown").mkdir(parents=True)
    (docs / "markdown" / "iso_9001.md").write_text("# ISO 9001 — Calidad\n\n" + texto_largo("calidad"), encoding="utf-8")
    emb = EmbeddingsControlados()
    emb.fijos.update({Q1: vec(1.0), Q2: vec(0.95), Q3: vec(0.80)})
    llm = LLMConEfecto("La calidad se mide con métricas. ¿Cómo la medirías tú?")
    clasificador = LLMFalso("PUNTUAL")
    reformulador = LLMFalso("¿Qué es la calidad del software?")
    redireccion = LLMFalso("Redirección")
    cache = CacheSemantico(tmp_path / "cache_respuestas.db", umbral=0.92)

    def crear(sincronizar=False):
        return RAGService(
            embeddings=emb, persist_dir=tmp_path / "bv", docs_dir=docs, sincronizar_al_iniciar=sincronizar,
            llm=llm.runnable(), llm_clasificador=clasificador.runnable(), llm_reformulador=reformulador.runnable(),
            llm_redireccion=redireccion.runnable(), cache=cache)

    servicio = crear()
    servicio.sincronizar()
    return SimpleNamespace(rag=servicio, llm=llm, clasificador=clasificador, reformulador=reformulador,
                           redireccion=redireccion, cache=cache, emb=emb, docs=docs, crear=crear)


def _llamadas(rig) -> int:
    return rig.llm.llamadas + rig.clasificador.llamadas + rig.reformulador.llamadas + rig.redireccion.llamadas


def test_pregunta_repetida_con_otra_redaccion_sale_del_cache_sin_llamar_al_llm(rig):
    r1 = rig.rag.get_answer(Q1)
    assert r1["desde_cache"] is False and r1["tiempo_respuesta_ms"] > 0 and r1["tipo"] == "respuesta"
    llamadas = _llamadas(rig)
    assert llamadas >= 1 and _entradas(rig.cache) == 1

    r2 = rig.rag.get_answer(Q2)                   # similitud 0.95 con Q1
    assert r2["desde_cache"] is True and r2["tipo"] == "respuesta"
    assert (r2["response"], r2["context"]) == (r1["response"], r1["context"])
    assert _llamadas(rig) == llamadas, "un acierto no debe llamar a ningún LLM"

    r3 = rig.rag.get_answer(Q1)                   # tercera vez: la misma pregunta
    assert r3["desde_cache"] is True and _llamadas(rig) == llamadas

    fila = _filas(rig.cache, "SELECT pregunta, usos, fuentes, tiempo_generacion_ms FROM respuestas")
    assert len(fila) == 1 and fila[0][0] == Q1 and fila[0][1] == 2 and fila[0][2] == '["iso_9001.md"]'
    e = rig.cache.estadisticas()
    assert (e["aciertos"], e["fallos"], e["tasa_aciertos"]) == (2, 1, pytest.approx(2 / 3, abs=1e-4))


def test_pregunta_por_debajo_del_umbral_se_genera_y_se_guarda_aparte(rig):
    rig.rag.get_answer(Q1)
    llamadas = rig.llm.llamadas
    r = rig.rag.get_answer(Q3)                    # similitud 0.80 < 0.92
    assert r["desde_cache"] is False and rig.llm.llamadas > llamadas and _entradas(rig.cache) == 2


def test_un_acierto_queda_en_la_memoria_de_la_conversacion(rig):
    rig.rag.get_answer(Q1, conversation_id="a")
    rig.rag.get_answer(Q2, conversation_id="b")                       # acierto
    rig.llm.respuesta = "Con un ejemplo."
    rig.rag.get_answer("Explícame eso mejor", conversation_id="b")    # seguimiento: usa el historial de "b"
    assert f"Estudiante: {Q2}" in rig.llm.prompts[-1]


def test_los_seguimientos_dentro_de_una_conversacion_no_pasan_por_el_cache(rig):
    rig.rag.get_answer(Q1, conversation_id="c")
    consultas = rig.cache.estadisticas()["consultas"]
    r = rig.rag.get_answer("Explícame eso mejor", conversation_id="c")
    assert r["desde_cache"] is False
    assert rig.cache.estadisticas()["consultas"] == consultas and _entradas(rig.cache) == 1


def test_saludos_preguntas_sobre_el_tutor_redirecciones_y_errores_no_se_guardan(rig, monkeypatch):
    assert rig.rag.get_answer("hola")["tipo"] == "saludo"
    assert rig.rag.get_answer("¿Qué puedes hacer?")["tipo"] == "funcionamiento"
    assert rig.cache.estadisticas()["consultas"] == 0

    monkeypatch.setattr(settings, "UMBRAL_PERTINENCIA", 2.0)   # ninguna pregunta llega: siempre candidata
    rig.clasificador.respuesta = "FUERA"
    for _ in range(2):
        r = rig.rag.get_answer("¿Cómo se hace un pastel?")
        assert r["tipo"] == "redireccion" and r["desde_cache"] is False
    assert rig.redireccion.llamadas == 2, "la redirección no se cachea: su redacción varía a propósito"

    rig.clasificador.respuesta = "DENTRO"
    rig.llm.respuesta = RuntimeError("Ollama caído")
    r = rig.rag.get_answer("¿Qué es la gestión de riesgos?")
    assert r["tipo"] == "error" and _entradas(rig.cache) == 0


def test_sin_contexto_si_se_guarda(rig):
    r = rig.rag.get_answer("¿Qué es Scrum?")     # término sin respaldo en los documentos
    assert r["tipo"] == "sin_contexto"
    assert _filas(rig.cache, "SELECT tipo FROM respuestas") == [("sin_contexto",)]


# ---------------------------------------------------------------- invalidación

def _subir(client, nombre, contenido):
    return client.post("/api/v1/documentos/subir",
                       files=[("archivos", (nombre, contenido, "application/octet-stream"))]).json()


@pytest.fixture
def cliente_docs(rig):
    app = FastAPI()
    app.include_router(documentos_router, prefix="/api/v1")
    app.dependency_overrides[get_rag_service] = lambda: rig.rag
    return TestClient(app)


def test_subir_un_documento_nuevo_invalida_el_cache(rig, cliente_docs):
    rig.rag.get_answer(Q1)
    assert _entradas(rig.cache) == 1
    resultado = _subir(cliente_docs, "riesgos.md", texto_largo("riesgos").encode())
    assert resultado["resultados"][0]["estado"] == "indexado"
    assert _entradas(rig.cache) == 0
    assert rig.rag.get_answer(Q2)["desde_cache"] is False, "la respuesta anterior ya no vale"
    e = rig.cache.estadisticas()
    assert e["invalidaciones"] >= 1 and "riesgos.md" in e["motivo_ultima_invalidacion"]


def test_subir_una_version_modificada_invalida_el_cache(rig, cliente_docs):
    _subir(cliente_docs, "riesgos.md", texto_largo("riesgos").encode())
    rig.rag.get_answer(Q1)
    _subir(cliente_docs, "riesgos.md", texto_largo("riesgos actualizados").encode())
    assert _entradas(rig.cache) == 0


def test_reenviar_el_mismo_archivo_no_cambia_el_indice_y_conserva_el_cache(rig, cliente_docs):
    contenido = texto_largo("riesgos").encode()
    _subir(cliente_docs, "riesgos.md", contenido)
    rig.rag.get_answer(Q1)
    assert _subir(cliente_docs, "riesgos.md", contenido)["resultados"][0]["estado"] == "omitido_sin_cambios"
    assert _entradas(rig.cache) == 1


def test_un_archivo_rechazado_no_invalida_el_cache(rig, cliente_docs):
    rig.rag.get_answer(Q1)
    assert _subir(cliente_docs, "malo.exe", b"MZ")["resultados"][0]["estado"] == "error"
    assert _entradas(rig.cache) == 1


def test_reindexar_invalida_el_cache(rig, cliente_docs):
    rig.rag.get_answer(Q1)
    assert _entradas(rig.cache) == 1
    assert cliente_docs.post("/api/v1/documentos/reindexar").status_code == 200
    assert _entradas(rig.cache) == 0
    assert rig.cache.estadisticas()["motivo_ultima_invalidacion"] == "reindexado completo"


def test_reindexar_descarta_tambien_lo_que_se_guarde_mientras_se_reconstruye(rig):
    original = rig.rag._indexar_todos

    def indexar_y_responder():
        resultados = original()
        rig.rag.get_answer(Q1)          # una consulta que llega a mitad del reindexado y se guarda
        assert _entradas(rig.cache) == 1
        return resultados
    rig.rag._indexar_todos = indexar_y_responder
    rig.rag.reconstruir()
    assert _entradas(rig.cache) == 0


def test_retirar_versiones_viejas_de_un_documento_ya_indexado_invalida_el_cache(rig, monkeypatch):
    md = rig.docs / "markdown" / "guia.md"
    md.write_text("# Guía\n\n" + texto_largo("uno"), encoding="utf-8")
    rig.rag.indexar_archivo(md)
    md.write_text("# Guía\n\n" + texto_largo("dos"), encoding="utf-8")
    borrar = rig.rag.vectorstore.delete
    monkeypatch.setattr(rig.rag.vectorstore, "delete", lambda **k: (_ for _ in ()).throw(RuntimeError("falla")))
    with pytest.raises(RuntimeError):
        rig.rag.indexar_archivo(md)     # añade la versión nueva y no logra borrar la vieja: quedan las dos
    monkeypatch.setattr(rig.rag.vectorstore, "delete", borrar)

    rig.rag.get_answer(Q1)
    assert _entradas(rig.cache) == 1
    assert rig.rag.indexar_archivo(md)[0] == "omitido_sin_cambios"   # contenido ya indexado; retira la vieja
    assert _entradas(rig.cache) == 0


def test_al_reiniciar_el_cache_persiste_si_los_documentos_no_cambiaron(rig):
    rig.rag.get_answer(Q1)
    llamadas = _llamadas(rig)
    reiniciado = rig.crear(sincronizar=True)         # servidor nuevo: sincroniza el índice al arrancar
    r = reiniciado.get_answer(Q2)
    assert r["desde_cache"] is True and _llamadas(rig) == llamadas


def test_al_reiniciar_invalida_si_un_documento_cambio_o_se_borro_mientras_estaba_apagado(rig):
    rig.rag.get_answer(Q1)
    (rig.docs / "markdown" / "iso_9001.md").write_text("# ISO 9001\n\n" + texto_largo("cambiado"), encoding="utf-8")
    reiniciado = rig.crear(sincronizar=True)
    assert _entradas(rig.cache) == 0 and reiniciado.get_answer(Q2)["desde_cache"] is False

    (rig.docs / "markdown" / "iso_9001.md").unlink()
    (rig.docs / "markdown" / "otro.md").write_text("# Otro\n\n" + texto_largo("otro"), encoding="utf-8")
    rig.rag.sincronizar()
    reiniciado.get_answer(Q1)
    (rig.docs / "markdown" / "otro.md").unlink()
    reiniciado.sincronizar()                          # poda de un documento borrado
    assert _entradas(rig.cache) == 0


def test_una_respuesta_generada_mientras_el_indice_cambia_no_se_guarda(rig):
    rig.llm.efecto = lambda: rig.cache.invalidar("carga concurrente")   # el índice cambia durante la generación
    r = rig.rag.get_answer(Q1)
    assert r["desde_cache"] is False and r["response"]
    assert _entradas(rig.cache) == 0


def test_si_falla_la_invalidacion_no_se_sirve_nada_del_cache_hasta_lograrla(rig, monkeypatch):
    rig.rag.get_answer(Q1)
    original = rig.cache.invalidar

    def falla(motivo=""):
        raise sqlite3.OperationalError("database is locked")
    monkeypatch.setattr(rig.cache, "invalidar", falla)
    rig.rag.indexar_archivo(_nuevo_md(rig))            # el documento se indexa aunque el caché no se pudo vaciar
    assert rig.rag._invalidacion_pendiente and _entradas(rig.cache) == 1

    assert rig.rag.get_answer(Q2)["desde_cache"] is False, "no debe servir la respuesta posiblemente vieja"
    monkeypatch.setattr(rig.cache, "invalidar", original)
    assert rig.rag.get_answer(Q2)["desde_cache"] is False   # reintenta: vacía el caché y responde de nuevo
    assert rig.rag._invalidacion_pendiente is None and _entradas(rig.cache) == 1
    assert rig.rag.get_answer(Q1)["desde_cache"] is True


def _nuevo_md(rig):
    ruta = rig.docs / "markdown" / "nuevo.md"
    ruta.write_text("# Nuevo\n\n" + texto_largo("nuevo"), encoding="utf-8")
    return ruta


def test_un_fallo_del_cache_nunca_impide_responder(rig, monkeypatch):
    def roto(*a, **k):
        raise sqlite3.DatabaseError("archivo corrupto")
    monkeypatch.setattr(rig.cache, "buscar", roto)
    assert rig.rag.get_answer(Q1)["response"]
    monkeypatch.undo()
    monkeypatch.setattr(rig.cache, "guardar", roto)
    r = rig.rag.get_answer(Q3)
    assert r["response"] and r["desde_cache"] is False


# ---------------------------------------------------------------- endpoints

@pytest.fixture
def cliente(rig, monkeypatch):
    monkeypatch.setattr(rag_module, "_instancia", rig.rag)   # evita crear el RAG real al importar chat
    import app.api.v1.endpoints.chat as chat_module
    monkeypatch.setattr(chat_module, "rag_service", rig.rag)
    app = FastAPI()
    app.include_router(chat_module.router, prefix="/api/v1")
    app.include_router(cache_router, prefix="/api/v1")
    app.dependency_overrides[get_rag_service] = lambda: rig.rag
    return TestClient(app)


def test_chat_informa_desde_cache_y_tiempo_en_ms(rig, cliente):
    rig.llm.efecto = lambda: time.sleep(0.05)       # la generación tarda ≥ 50 ms; el acierto, casi nada
    primero = cliente.post("/api/v1/chat", json={"message": Q1}).json()
    segundo = cliente.post("/api/v1/chat", json={"message": Q2}).json()
    assert primero["desde_cache"] is False and primero["tiempo_respuesta_ms"] >= 50
    assert segundo["desde_cache"] is True and segundo["tiempo_respuesta_ms"] < primero["tiempo_respuesta_ms"]
    assert segundo["response"] == primero["response"] and segundo["tipo"] == "respuesta"
    assert cliente.post("/api/v1/chat", json={"message": "hola"}).json()["desde_cache"] is False


def test_endpoint_de_estadisticas(rig, cliente):
    rig.llm.efecto = lambda: time.sleep(0.05)
    for pregunta in (Q1, Q2, Q1, Q3):
        cliente.post("/api/v1/chat", json={"message": pregunta})
    r = cliente.get("/api/v1/cache/estadisticas")
    assert r.status_code == 200
    e = r.json()
    assert e["total_entradas"] == 2                       # Q1 (con Q2 y Q1 repetidas) y Q3
    assert (e["aciertos"], e["fallos"], e["tasa_aciertos"]) == (2, 2, 0.5)
    assert e["preguntas_mas_repetidas"][0]["pregunta"] == Q1 and e["preguntas_mas_repetidas"][0]["usos"] == 2
    assert len(e["preguntas_mas_repetidas"]) == 1         # Q3 nunca se repitió
    assert e["tiempo_promedio_ahorrado_ms"] > 0 and e["umbral_similitud"] == 0.92
    assert {"invalidaciones", "ultima_invalidacion", "tiempo_total_ahorrado_ms", "consultas"} <= set(e)


def test_estadisticas_responde_503_si_el_cache_esta_desactivado(rag):
    app = FastAPI()
    app.include_router(cache_router, prefix="/api/v1")
    app.dependency_overrides[get_rag_service] = lambda: rag      # `rag` de conftest: caché apagado
    assert TestClient(app).get("/api/v1/cache/estadisticas").status_code == 503
