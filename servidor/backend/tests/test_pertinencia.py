import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from langchain_core.embeddings import DeterministicFakeEmbedding
from langchain_core.runnables import RunnableLambda

import app.services.rag_service as rag_module
from app.core.config import settings
from app.services import pertinencia_service as pertinencia
from app.services.rag_service import RAGService
from tests.conftest import LLMFalso, texto_largo

PERTINENCIA = "clasificador de preguntas"   # texto del prompt DENTRO/FUERA
SIEMPRE_PERTINENTE = -1.0   # similitud coseno >= -1: nada es candidato
SIEMPRE_CANDIDATA = 2.0     # similitud coseno < 2: todo es candidato


@pytest.fixture
def llms():
    return {"llm": LLMFalso("Respuesta con contexto"), "clasificador": LLMFalso("DENTRO"),
            "redireccion": LLMFalso("Qué curiosa pregunta; yo me enfoco en normativas...")}


@pytest.fixture
def tutor(tmp_path, docs, llms):
    (docs / "markdown").mkdir(parents=True)
    servicio = RAGService(
        embeddings=DeterministicFakeEmbedding(size=32),
        persist_dir=tmp_path / "base_vectorial",
        docs_dir=docs,
        sincronizar_al_iniciar=False,
        llm=llms["llm"].runnable(),
        llm_clasificador=llms["clasificador"].runnable(),
        llm_redireccion=llms["redireccion"].runnable(),
    )
    (docs / "markdown" / "iso_9001.md").write_text(texto_largo("calidad"), encoding="utf-8")
    servicio.sincronizar()
    return servicio


@pytest.fixture(autouse=True)
def filtro_activo(monkeypatch):
    monkeypatch.setattr(settings, "FILTRO_PERTINENCIA_ACTIVO", True)


# ---------------------------------------------------------------- funciones puras

@pytest.mark.parametrize("pregunta", [
    "¿Qué puedes hacer?",
    "que puedes hacer",
    "¿Qué documentos tienes?",
    "¿De qué temas me puedes ayudar?",
    "¿En qué me puedes ayudar?",
    "¿Con qué normas puedes ayudarme?",
    "¿Qué normativas manejas?",
    "Quién eres y cómo funcionas",
    "¿Para qué sirves?",
    "¿Sobre qué temas te puedo preguntar?",
    "¿Qué documentos tienes cargados?",
])
def test_preguntas_sobre_el_tutor_se_detectan(pregunta):
    assert pertinencia.es_pregunta_sobre_tutor(pregunta)


@pytest.mark.parametrize("pregunta", [
    "¿Qué es la ISO 9001?",
    "¿Qué documentos hay que presentar en una auditoría ISO 9001?",
    "¿Me puedes ayudar con la receta de un pastel?",
    "¿Puedes explicarme qué es un riesgo residual?",
    "¿De qué trata la norma ISO 27001?",
    "¿Qué normas debo aplicar en un proyecto de software?",
    "¿Cómo funciona el ciclo PDCA?",
])
def test_preguntas_de_contenido_no_son_sobre_el_tutor(pregunta):
    assert not pertinencia.es_pregunta_sobre_tutor(pregunta)


@pytest.mark.parametrize("texto,esperado", [
    ("DENTRO", "DENTRO"), ("FUERA", "FUERA"), ("  fuera.\n", "FUERA"), ("Dentro", "DENTRO"),
    ("**FUERA**", "FUERA"), ("FUERA del temario", "FUERA"),
    ("", None), ("no lo sé", None), ("DENTRO o FUERA", None),
])
def test_parsear_clasificacion(texto, esperado):
    assert pertinencia.parsear_clasificacion(texto) == esperado


@pytest.mark.parametrize("texto,esperado", [
    ("NINGUNO", []), ("NINGUNO.", []), ("", []), ("3, 7, 15", [3, 7, 15]), ("2", [2]),
    ("1, 2, 3, 4, 5", [1, 2, 3]),        # máximo 3
    ("5, 5, 9", [5, 9]),                 # sin repetidos
    ("0, 99, 4", [4]),                   # fuera de rango se ignora
])
def test_parsear_temas(texto, esperado):
    assert pertinencia.parsear_temas(texto, total=24) == esperado


def test_redireccion_propone_los_temas_elegidos_y_no_fuerza_conexiones():
    seleccion = LLMFalso("1, 2")
    redaccion = LLMFalso("texto redactado")
    pertinencia.generar_redireccion(redaccion.runnable(), "¿Cómo protejo mi cuenta?", seleccion.runnable())
    prompt = redaccion.prompts[0]
    assert "«¿Cómo protejo mi cuenta?»" in prompt
    assert "- Unidad 1: marcos predictivos" in prompt and "- Unidad 1: Scrum, Kanban y Lean" in prompt
    assert "Ningún tema" not in prompt

    seleccion.respuesta = "NINGUNO"
    pertinencia.generar_redireccion(redaccion.runnable(), "¿Cómo se prepara el ceviche?", seleccion.runnable())
    prompt = redaccion.prompts[1]
    assert "Ningún tema de la asignatura tiene relación directa" in prompt
    assert "no fuerces" in prompt and "Unidad 4: Gestión de pruebas" in prompt


def test_redireccion_sigue_funcionando_si_falla_la_seleccion_de_temas():
    seleccion = LLMFalso(RuntimeError("Ollama caído"))
    redaccion = LLMFalso("texto redactado")
    assert pertinencia.generar_redireccion(redaccion.runnable(), "¿Y esto?", seleccion.runnable()) == "texto redactado"


# ---------------------------------------------------------------- flujo de get_answer

def test_saludo_pasa_sin_filtro_ni_llm(tutor, llms, monkeypatch):
    monkeypatch.setattr(settings, "UMBRAL_PERTINENCIA", SIEMPRE_CANDIDATA)
    r = tutor.get_answer("hola")
    assert r["tipo"] == "saludo"
    assert llms["llm"].llamadas == llms["clasificador"].llamadas == llms["redireccion"].llamadas == 0


@pytest.mark.parametrize("pregunta", ["¿Qué puedes hacer?", "¿Qué documentos tienes?", "¿De qué temas me puedes ayudar?"])
def test_preguntas_sobre_el_tutor_pasan_sin_filtro(tutor, llms, monkeypatch, pregunta):
    monkeypatch.setattr(settings, "UMBRAL_PERTINENCIA", SIEMPRE_CANDIDATA)
    r = tutor.get_answer(pregunta)
    assert r["tipo"] == "funcionamiento"
    assert llms["clasificador"].llamadas == llms["redireccion"].llamadas == 0
    prompt = llms["llm"].prompts[-1]
    assert "iso 9001" in prompt, "debe informar de los documentos realmente cargados"
    assert "Unidad 3" in prompt, "y del temario"


def test_pregunta_pertinente_no_llama_al_clasificador(tutor, llms, monkeypatch):
    monkeypatch.setattr(settings, "UMBRAL_PERTINENCIA", SIEMPRE_PERTINENTE)
    r = tutor.get_answer("¿Qué es la calidad?")
    assert r["tipo"] == "respuesta" and r["response"] == "Respuesta con contexto"
    assert llms["clasificador"].llamadas_con(PERTINENCIA) == llms["redireccion"].llamadas == 0


def test_candidata_confirmada_dentro_se_responde_con_el_rag(tutor, llms, monkeypatch):
    monkeypatch.setattr(settings, "UMBRAL_PERTINENCIA", SIEMPRE_CANDIDATA)
    llms["clasificador"].respuesta = "DENTRO"
    r = tutor.get_answer("¿Qué es un plan de calidad?")
    assert r["tipo"] == "respuesta" and r["response"] == "Respuesta con contexto"
    assert llms["clasificador"].llamadas_con(PERTINENCIA) == 1 and llms["redireccion"].llamadas == 0


def test_candidata_fuera_redirige_y_no_responde_el_contenido(tutor, llms, monkeypatch):
    monkeypatch.setattr(settings, "UMBRAL_PERTINENCIA", SIEMPRE_CANDIDATA)
    llms["clasificador"].respuesta = "FUERA"
    r = tutor.get_answer("¿Cómo preparo un pastel de chocolate?")
    assert r["tipo"] == "redireccion"
    assert r["response"] == llms["redireccion"].respuesta, "la redirección la redacta el LLM"
    assert llms["llm"].llamadas == 0, "no se llama al LLM de respuesta para el contenido"
    assert r["context"] == ""
    prompt_redireccion = llms["redireccion"].prompts[0]
    assert "pastel de chocolate" in prompt_redireccion and "Unidad 2" in prompt_redireccion
    assert "Unidad 4" in llms["clasificador"].prompts[0], "el clasificador recibe la lista de unidades"


def test_redirecciones_varian_segun_lo_que_genera_el_llm(tutor, llms, monkeypatch):
    monkeypatch.setattr(settings, "UMBRAL_PERTINENCIA", SIEMPRE_CANDIDATA)
    llms["clasificador"].respuesta = "FUERA"
    textos = iter(["Redacción uno", "Redacción dos", "Redacción tres"])
    llms["redireccion"].respuesta = None
    tutor.llm_redireccion = RunnableLambda(lambda pv: next(textos))
    respuestas = {tutor.get_answer("¿Quién ganó el mundial?")["response"] for _ in range(3)}
    assert len(respuestas) == 3


@pytest.mark.parametrize("respuesta_clasificador", ["no sé qué decir", "", "DENTRO o FUERA", RuntimeError("Ollama caído")])
def test_clasificacion_no_interpretable_no_bloquea_al_estudiante(tutor, llms, monkeypatch, respuesta_clasificador):
    monkeypatch.setattr(settings, "UMBRAL_PERTINENCIA", SIEMPRE_CANDIDATA)
    llms["clasificador"].respuesta = respuesta_clasificador
    r = tutor.get_answer("¿Qué es la deuda técnica?")
    assert r["tipo"] == "respuesta" and llms["redireccion"].llamadas == 0


def test_error_al_redactar_la_redireccion_se_reporta_como_error(tutor, llms, monkeypatch):
    monkeypatch.setattr(settings, "UMBRAL_PERTINENCIA", SIEMPRE_CANDIDATA)
    llms["clasificador"].respuesta = "FUERA"
    llms["redireccion"].respuesta = RuntimeError("Ollama caído")
    assert tutor.get_answer("¿Cuál es la capital de Australia?")["tipo"] == "error"


def test_filtro_desactivado_no_clasifica_ni_redirige(tutor, llms, monkeypatch):
    monkeypatch.setattr(settings, "FILTRO_PERTINENCIA_ACTIVO", False)
    monkeypatch.setattr(settings, "UMBRAL_PERTINENCIA", SIEMPRE_CANDIDATA)
    llms["clasificador"].respuesta = "FUERA"
    r = tutor.get_answer("¿Cuál es la capital de Australia?")
    assert r["tipo"] == "respuesta"
    assert llms["clasificador"].llamadas_con(PERTINENCIA) == 0


def test_sin_documentos_no_redirige(tmp_path, docs, llms, monkeypatch):
    (docs / "markdown").mkdir(parents=True)
    vacio = RAGService(embeddings=DeterministicFakeEmbedding(size=32), persist_dir=tmp_path / "bv",
                       docs_dir=docs, sincronizar_al_iniciar=False, llm=llms["llm"].runnable(),
                       llm_clasificador=llms["clasificador"].runnable(),
                       llm_redireccion=llms["redireccion"].runnable())
    assert vacio.get_answer("¿Qué es ISO 9001?")["tipo"] == "sin_documentos"


def test_score_es_similitud_coseno(tutor):
    resultados = tutor.buscar_con_score("Contenido de calidad, parte 1.")
    assert resultados and all(-1.0 <= s <= 1.0 for _, s in resultados)
    assert tutor._espacio_distancia() == "cosine"


# ---------------------------------------------------------------- endpoint /chat

def test_endpoint_chat_expone_el_tipo(tutor, llms, monkeypatch):
    monkeypatch.setattr(rag_module, "_instancia", tutor)   # evita crear el RAG real al importar chat
    import app.api.v1.endpoints.chat as chat_module
    monkeypatch.setattr(chat_module, "rag_service", tutor)  # chat.py lo fija al importarse
    router = chat_module.router

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    cliente = TestClient(app)

    monkeypatch.setattr(settings, "UMBRAL_PERTINENCIA", SIEMPRE_CANDIDATA)
    llms["clasificador"].respuesta = "FUERA"
    datos = cliente.post("/api/v1/chat", json={"message": "¿Cómo se hace un pastel?"}).json()
    assert datos["tipo"] == "redireccion" and datos["status"] == "success" and datos["response"]

    assert cliente.post("/api/v1/chat", json={"message": "hola"}).json()["tipo"] == "saludo"
    monkeypatch.setattr(settings, "UMBRAL_PERTINENCIA", SIEMPRE_PERTINENTE)
    assert cliente.post("/api/v1/chat", json={"message": "¿Qué es la calidad?"}).json()["tipo"] == "respuesta"
