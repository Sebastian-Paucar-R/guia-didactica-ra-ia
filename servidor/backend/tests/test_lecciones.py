"""leccion_id (app Flutter) -> tema del sílabo a priorizar al recuperar contexto. Dos partes: core/lecciones.py
en aislamiento (el mapeo, sin servidor) y RAGService._flujo con una lección resuelta (filtra la recuperación a
los documentos de esa lección y salta el filtro de pertinencia normal, ver CLAUDE.md "Relevance filter")."""
import json

import pytest
from langchain_core.embeddings import DeterministicFakeEmbedding

from app.core import lecciones, silabo
from app.core.config import settings
from app.services.rag_service import RAGService
from tests.conftest import LLMFalso, texto_largo

# ---------------------------------------------------------------- core/lecciones.py


@pytest.fixture(autouse=True)
def _limpiar_cache_lecciones():
    lecciones._cargar.cache_clear()
    yield
    lecciones._cargar.cache_clear()


def _tema_real() -> silabo.Tema:
    return silabo.temas()[0]


def test_leccion_sin_mapear_no_resuelve_nada(tmp_path):
    ruta = tmp_path / "lecciones.json"
    ruta.write_text(json.dumps({"lecciones": {}}), encoding="utf-8")
    assert lecciones.resolver_leccion(None, ruta) is None
    assert lecciones.resolver_leccion("leccion-inexistente", ruta) is None


def test_leccion_mapeada_resuelve_al_tema_del_silabo(tmp_path):
    tema = _tema_real()
    ruta = tmp_path / "lecciones.json"
    ruta.write_text(json.dumps({"lecciones": {"leccion-x": tema.id}}), encoding="utf-8")
    resuelto = lecciones.resolver_leccion("leccion-x", ruta)
    assert resuelto is not None and resuelto.id == tema.id and resuelto.nombre == tema.nombre


def test_leccion_con_tema_inexistente_se_ignora_sin_romper(tmp_path, capsys):
    ruta = tmp_path / "lecciones.json"
    ruta.write_text(json.dumps({"lecciones": {"leccion-rota": "99.9"}}), encoding="utf-8")
    assert lecciones.resolver_leccion("leccion-rota", ruta) is None
    assert "no existe en el sílabo" in capsys.readouterr().out


def test_sin_archivo_de_lecciones_no_rompe(tmp_path):
    assert lecciones.resolver_leccion("cualquiera", tmp_path / "no_existe.json") is None


# ---------------------------------------------------------------- RAGService._flujo con leccion_id


PREGUNTA_SIN_TEMA = "¿Cómo se hace un pastel?"   # fuera de tema, ya probado en test_pertinencia.py


@pytest.fixture
def llms():
    # "FUERA" (no un tema): fuerza la redirección cuando NO hay lección, que es justo lo que se compara contra
    # el camino con lección. El mismo clasificador también decide la intención (ver tutor_service.py); un
    # veredicto que no es PUNTUAL/PROFUNDIZAR/TAREA cae a PUNTUAL por defecto, así que no afecta esa parte.
    return {"llm": LLMFalso("La respuesta normal del tutor."),
            "clasificador": LLMFalso("FUERA"),
            "reformulador": LLMFalso(PREGUNTA_SIN_TEMA),
            "redireccion": LLMFalso("Redirección")}


@pytest.fixture
def tutor_con_leccion(tmp_path, docs, llms, monkeypatch):
    # Fuera de tema por defecto (umbral imposible de superar): así se comprueba que la lección, no el filtro
    # normal de pertinencia, es lo que decide la ubicación.
    monkeypatch.setattr(settings, "UMBRAL_PERTINENCIA", 2.0)
    (docs / "markdown").mkdir(parents=True)
    (docs / "markdown" / "iso_9001.md").write_text("# ISO 9001 — Calidad\n\n" + texto_largo("calidad"), encoding="utf-8")
    (docs / "markdown" / "otra_norma.md").write_text("# Otra norma\n\n" + texto_largo("otra norma"), encoding="utf-8")
    servicio = RAGService(
        embeddings=DeterministicFakeEmbedding(size=32), persist_dir=tmp_path / "bv", docs_dir=docs,
        sincronizar_al_iniciar=False, llm=llms["llm"].runnable(), llm_clasificador=llms["clasificador"].runnable(),
        llm_reformulador=llms["reformulador"].runnable(), llm_redireccion=llms["redireccion"].runnable())
    servicio.sincronizar()

    tema_leccion = silabo.Tema(id="2.2", nombre="ISO 9001", unidad=2, unidad_titulo="Normativas",
                               palabras_clave=(), archivos=("iso_9001.md",))
    monkeypatch.setattr(lecciones, "resolver_leccion", lambda leccion_id, ruta=None: (
        tema_leccion if leccion_id == "leccion-iso-9001" else None))
    return servicio


def test_leccion_fuerza_la_ubicacion_sin_pasar_por_el_filtro_normal(tutor_con_leccion):
    r = tutor_con_leccion.get_answer(PREGUNTA_SIN_TEMA, leccion_id="leccion-iso-9001")
    assert r["tipo"] == "respuesta"
    ub = r["ubicacion"]
    assert ub["metodo"] == "leccion" and ub["tema_id"] == "2.2" and ub["unidad"] == 2


def test_sin_leccion_la_misma_pregunta_se_redirige(tutor_con_leccion):
    r = tutor_con_leccion.get_answer(PREGUNTA_SIN_TEMA)
    assert r["tipo"] == "redireccion"


def test_leccion_id_desconocido_no_fuerza_nada(tutor_con_leccion):
    r = tutor_con_leccion.get_answer(PREGUNTA_SIN_TEMA, leccion_id="leccion-que-no-existe")
    assert r["tipo"] == "redireccion"


def test_respuesta_de_leccion_no_se_guarda_en_cache(tmp_path, tutor_con_leccion):
    from app.services.cache_service import CacheSemantico
    tutor_con_leccion.cache = CacheSemantico(tmp_path / "cache.db", 0.95)
    tutor_con_leccion.get_answer(PREGUNTA_SIN_TEMA, conversation_id="a", leccion_id="leccion-iso-9001")
    assert tutor_con_leccion.cache.estadisticas()["total_entradas"] == 0
    assert tutor_con_leccion.probar_cache(PREGUNTA_SIN_TEMA, conversation_id="b",
                                          leccion_id="leccion-iso-9001") is None
