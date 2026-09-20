import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from langchain_core.embeddings import DeterministicFakeEmbedding

import app.services.rag_service as rag_module
from app.core.config import settings
from app.services import tutor_service as tutor
from app.services.memoria_service import MemoriaConversacional
from app.services.rag_service import RAGService
from tests.conftest import LLMFalso, texto_largo

NL = chr(10)
MODO_PUNTUAL = "hace una pregunta puntual"
MODO_PROFUNDIZAR = "pide profundizar"
MODO_TAREA = "No lo entregues resuelto"


# ---------------------------------------------------------------- memoria

def test_memoria_acota_turnos_y_conversaciones():
    m = MemoriaConversacional(max_turnos=3, max_conversaciones=2)
    for i in range(5):
        m.agregar("a", f"p{i}", f"r{i}")
    assert [t.pregunta for t in m.obtener("a")] == ["p2", "p3", "p4"]
    assert [t.pregunta for t in m.obtener("a", ultimos=2)] == ["p3", "p4"]
    m.agregar("b", "x", "y")
    m.obtener("a")                    # leer no cuenta como uso; agregar sí
    m.agregar("c", "x", "y")          # desaloja la menos reciente ("a")
    assert m.obtener("a") == [] and len(m) == 2


def test_memoria_sin_id_no_guarda():
    m = MemoriaConversacional()
    m.agregar(None, "p", "r")
    m.agregar("", "p", "r")
    assert len(m) == 0 and m.obtener(None) == []


# ---------------------------------------------------------------- intención

@pytest.mark.parametrize("mensaje,esperada", [
    ("Explícame eso mejor", tutor.PROFUNDIZAR),
    ("no entendí, ¿puedes ampliar la parte de los controles?", tutor.PROFUNDIZAR),
    ("dame un ejemplo aplicado a una app web", tutor.PROFUNDIZAR),
    ("profundiza en el ciclo PDCA", tutor.PROFUNDIZAR),
    ("Resuélveme este ejercicio de riesgos", tutor.TAREA),
    ("Redáctame el plan de auditoría, dame la respuesta completa", tutor.TAREA),
    ("hazlo por mí, por favor", tutor.TAREA),
    ("Redáctame un ejemplo de informe", tutor.TAREA),          # TAREA gana a "ejemplo"
    ("¿Qué es la mejora continua?", None),
    ("¿Cuál es la diferencia entre ISO 27001 e ISO 27002?", None),
    ("¿Cuándo aplica la ISO 9001?", None),
])
def test_intencion_por_senales(mensaje, esperada):
    assert tutor.detectar_intencion_por_senales(mensaje) == esperada


@pytest.mark.parametrize("texto,esperada", [
    ("PUNTUAL", "PUNTUAL"), ("profundizar.", "PROFUNDIZAR"), ("**TAREA**", "TAREA"),
    ("PUNTUAL o TAREA", None), ("", None), ("no sé", None),
])
def test_parsear_intencion(texto, esperada):
    assert tutor.parsear_intencion(texto) == esperada


def test_intencion_sin_senales_usa_el_llm_y_ante_la_duda_es_puntual():
    assert tutor.detectar_intencion(LLMFalso("TAREA").runnable(), "necesito que armes mi informe") == tutor.TAREA
    assert tutor.detectar_intencion(LLMFalso("???").runnable(), "¿qué es un SGSI?") == tutor.PUNTUAL
    assert tutor.detectar_intencion(LLMFalso(RuntimeError("caído")).runnable(), "¿qué es un SGSI?") == tutor.PUNTUAL


# ---------------------------------------------------------------- verificación de citas

RESPALDO = "[Documento: ISO_9001] ISO 9001 — Sistemas de Gestión de la Calidad. ISO/IEC 25010:2023 cláusula 4 y 7.2"


@pytest.mark.parametrize("respuesta,invalidas", [
    ("Según ISO 9001 se planifica la mejora.", []),
    ("La ISO/IEC 25010:2023 define la calidad.", []),
    ("La ISO 27005 trata de riesgos.", ["ISO 27005"]),
    ("Ver ISO/IEC 25010:2011.", ["ISO/IEC 25010:2011"]),
    ("La cláusula 7.2 habla de competencia.", []),
    ("La cláusula 9.3 habla de la revisión.", ["cláusula 9.3"]),
    ("Sin normas ni cláusulas aquí.", []),
    ("ISO 12345 e ISO 12345 otra vez.", ["ISO 12345"]),
    ("Los controles están organizados en 11 claves de control.", ["11 claves de control"]),
    ("La norma tiene 7 cláusulas.", ["7 cláusulas"]),
    ("La norma tiene 4 cláusulas y 25010 la complementa.", []),        # '4' figura en el respaldo
    ("El equipo mejora un 20% en 6 semanas.", []),                     # cifras de un ejemplo no se controlan
])
def test_normas_no_respaldadas(respuesta, invalidas):
    assert tutor.normas_no_respaldadas(respuesta, RESPALDO) == invalidas


def test_quitar_oraciones_con_normas_inventadas():
    texto = "La calidad se mide. La ISO 27005 lo exige. Conviene revisar los procesos."
    assert tutor.quitar_oraciones_con(texto, ["ISO 27005"]) == "La calidad se mide. Conviene revisar los procesos."
    assert tutor.quitar_oraciones_con("Solo ISO 27005.", ["ISO 27005"]) == "Solo ISO 27005."   # no deja vacío


@pytest.mark.parametrize("entrada,salida", [
    ("Excelente pregunta. La calidad se mide.", "La calidad se mide."),
    ("¡Excelente pregunta! ¿Sabías que...? Sí.", "¿Sabías que...? Sí."),
    ("Claro, la calidad se mide.", "La calidad se mide."),
    ("¡Por supuesto! Se mide con métricas.", "Se mide con métricas."),
    ("La calidad se mide con métricas.", "La calidad se mide con métricas."),
    ("Claro está que no aplica.", "Claro está que no aplica."),
    ("Hola, ¿cómo estás? Entiendo que tienes una duda sobre Scrum. No aparece en los documentos.",
     "No aparece en los documentos."),
    ("Lo siento, pero eso no aparece en los documentos.", "Eso no aparece en los documentos."),
    ("¿Cómo puedo ayudarte? La norma 29119 no aparece.", "La norma 29119 no aparece."),
    ("Entiendo que quieres saber de ISO 9001. La norma define la calidad.", "La norma define la calidad."),
    ("¿cómo se mide? Con métricas.", "¿Cómo se mide? Con métricas."),
])
def test_limpiar_preambulo(entrada, salida):
    assert tutor.limpiar_preambulo(entrada) == salida


def test_quitar_encabezado_colgado():
    assert tutor.quitar_encabezado_colgado("Texto final." + NL + NL + "Referencias:") == "Texto final."
    assert tutor.quitar_encabezado_colgado("Pasos:" + NL + "1. Uno") == "Pasos:" + NL + "1. Uno"
    assert tutor.quitar_encabezado_colgado("Solo una línea:") == "Solo una línea:"


def test_formatear_contexto_indica_el_documento():
    texto = tutor.formatear_contexto([("ISO_9001_Gestion_Calidad.md", "ISO 9001 — Gestión de la Calidad", "texto uno")])
    assert "[Documento: ISO_9001_Gestion_Calidad — «ISO 9001 — Gestión de la Calidad»]" in texto and "texto uno" in texto


# ---------------------------------------------------------------- flujo con memoria y modos

@pytest.fixture
def llms():
    return {"llm": LLMFalso("La calidad se mide con métricas. ¿Cómo la medirías tú?"),
            "clasificador": LLMFalso("PUNTUAL"),
            "reformulador": LLMFalso("¿Qué es la calidad del software?"),
            "redireccion": LLMFalso("Redirección")}


@pytest.fixture
def tutor_rag(tmp_path, docs, llms, monkeypatch):
    monkeypatch.setattr(settings, "UMBRAL_PERTINENCIA", -1.0)   # todo pertinente: aquí se prueba el tutor
    (docs / "markdown").mkdir(parents=True)
    (docs / "markdown" / "iso_9001.md").write_text("# ISO 9001 — Calidad\n\n" + texto_largo("calidad"), encoding="utf-8")
    servicio = RAGService(
        embeddings=DeterministicFakeEmbedding(size=32), persist_dir=tmp_path / "bv", docs_dir=docs,
        sincronizar_al_iniciar=False, llm=llms["llm"].runnable(), llm_clasificador=llms["clasificador"].runnable(),
        llm_reformulador=llms["reformulador"].runnable(), llm_redireccion=llms["redireccion"].runnable())
    servicio.sincronizar()
    return servicio


GUIA_NUMERADA = NL.join(["1. Define el alcance de tu auditoría interna de calidad y sus límites.",
                         "2. Identifica los procesos clave y qué evidencia genera cada uno.",
                         "3. Prepara las preguntas guía para cada proceso auditado.",
                         "4. Comparte tu primer borrador para revisarlo juntos y ajustar lo que haga falta antes de entregarlo."])


def _ultimo_prompt(llms):
    return llms["llm"].prompts[-1]


@pytest.mark.parametrize("mensaje,modo", [
    ("¿Qué es la calidad?", MODO_PUNTUAL),
    ("Explícame eso mejor con un ejemplo", MODO_PROFUNDIZAR),
    ("Resuélveme el ejercicio de auditoría", MODO_TAREA),
])
def test_el_prompt_lleva_el_modo_segun_la_intencion(tutor_rag, llms, mensaje, modo):
    assert tutor_rag.get_answer(mensaje)["tipo"] == "respuesta"
    prompt = _ultimo_prompt(llms)
    assert modo in prompt
    assert sum(m in prompt for m in (MODO_PUNTUAL, MODO_PROFUNDIZAR, MODO_TAREA)) == 1, "solo el modo detectado"


def test_el_prompt_incluye_reglas_documentos_silabo_y_fuente_del_contexto(tutor_rag, llms):
    tutor_rag.get_answer("¿Qué es la calidad?")
    prompt = _ultimo_prompt(llms)
    assert "iso_9001" in prompt and "Unidad 4:" in prompt
    assert "[Documento: iso_9001 — «ISO 9001 — Calidad»]" in prompt
    assert "No inventes normas" in prompt and "Nunca entregas resuelto" in prompt


def test_clasificador_sin_senales_decide_la_intencion(tutor_rag, llms):
    llms["clasificador"].respuesta = "PROFUNDIZAR"
    tutor_rag.get_answer("y qué más se puede decir de eso?")
    assert MODO_PROFUNDIZAR in _ultimo_prompt(llms)


def test_memoria_el_seguimiento_recuerda_el_tema(tutor_rag, llms):
    tutor_rag.get_answer("¿Qué es la calidad del software?", conversation_id="c1")
    assert llms["reformulador"].llamadas == 0, "sin historial no hay reformulación"

    llms["llm"].respuesta = "Desarrollo largo con ejemplo."
    r = tutor_rag.get_answer("Explícame eso mejor", conversation_id="c1")
    assert r["response"] == "Desarrollo largo con ejemplo."
    prompt = _ultimo_prompt(llms)
    assert "Estudiante: ¿Qué es la calidad del software?" in prompt and "Tutor: La calidad se mide" in prompt
    assert "(Se refiere a: ¿Qué es la calidad del software?)" in prompt
    assert llms["reformulador"].llamadas == 1
    assert "Explícame eso mejor" in llms["reformulador"].prompts[0] and "¿Qué es la calidad del software?" in llms["reformulador"].prompts[0]


def test_memoria_es_por_conversacion(tutor_rag, llms):
    tutor_rag.get_answer("¿Qué es la calidad del software?", conversation_id="c1")
    tutor_rag.get_answer("Explícame eso mejor", conversation_id="c2")
    assert llms["reformulador"].llamadas == 0
    assert "primer mensaje de la conversación" in _ultimo_prompt(llms)


def test_sin_conversation_id_no_se_recuerda_nada(tutor_rag, llms):
    tutor_rag.get_answer("¿Qué es la calidad?")
    tutor_rag.get_answer("Explícame eso mejor")
    assert len(tutor_rag.memoria) == 0 and llms["reformulador"].llamadas == 0


def test_saludo_y_errores_no_entran_en_la_memoria(tutor_rag, llms):
    tutor_rag.get_answer("hola", conversation_id="c1")
    assert tutor_rag.memoria.obtener("c1") == []
    llms["llm"].respuesta = RuntimeError("Ollama caído")
    assert tutor_rag.get_answer("¿Qué es la calidad?", conversation_id="c1")["tipo"] == "error"
    assert tutor_rag.memoria.obtener("c1") == []


def test_el_filtro_usa_la_pregunta_autonoma_del_seguimiento(tutor_rag, llms, monkeypatch):
    """'explícame eso' solo no significa nada: se clasifica y recupera con la pregunta reescrita."""
    tutor_rag.get_answer("¿Qué es la calidad del software?", conversation_id="c1")
    monkeypatch.setattr(settings, "UMBRAL_PERTINENCIA", 2.0)     # ahora todo es candidato
    llms["clasificador"].respuesta = ["DENTRO"]
    tutor_rag.get_answer("Explícame eso mejor", conversation_id="c1")
    prompt_pertinencia = next(p for p in llms["clasificador"].prompts if "clasificador de preguntas" in p)
    assert "Mensaje: ¿Qué es la calidad del software?" in prompt_pertinencia


@pytest.mark.parametrize("mensaje,es", [
    ("Explícame eso mejor", True), ("Amplía eso de los controles, no me quedó claro", True),
    ("No entendí muy bien, ¿me lo explicas mejor con un ejemplo?", True), ("¿Y eso cómo se aplica?", True),
    ("¿Y la 27002?", True),                                        # muy corto
    ("¿Qué es un SGSI?", False), ("¿Cuándo aplica la ISO 9001?", False),
    ("¿Cuál es la diferencia entre ISO/IEC 27001 e ISO/IEC 27002?", False),
])
def test_solo_se_reescriben_los_seguimientos(mensaje, es):
    assert tutor.es_seguimiento(mensaje) is es


def test_pregunta_independiente_no_se_reescribe_aunque_haya_historial(tutor_rag, llms):
    tutor_rag.get_answer("¿Qué es la calidad del software?", conversation_id="c1")
    tutor_rag.get_answer("¿Cuándo aplica la ISO 9001 en una empresa pequeña?", conversation_id="c1")
    assert llms["reformulador"].llamadas == 0


def test_la_reescritura_se_queda_con_la_primera_pregunta():
    from app.services.memoria_service import Turno
    llm = LLMFalso("¿Qué es un SGSI? ¿Es un tipo de ciclo PDCA? ¿Cómo se diferencia?").runnable()
    assert tutor.reformular_pregunta(llm, "Explícame eso", [Turno("q", "a")]) == "¿Qué es un SGSI?"


def test_reformulacion_fallida_o_absurda_usa_la_pregunta_original():
    from app.services.memoria_service import Turno
    turnos = [Turno("¿Qué es ISO 9001?", "Es una norma de calidad.")]
    assert tutor.reformular_pregunta(LLMFalso(RuntimeError("x")).runnable(), "Explícame eso", turnos) == "Explícame eso"
    assert tutor.reformular_pregunta(LLMFalso("x" * 500).runnable(), "Explícame eso", turnos) == "Explícame eso"
    assert tutor.reformular_pregunta(LLMFalso("").runnable(), "Explícame eso", turnos) == "Explícame eso"
    assert tutor.reformular_pregunta(LLMFalso("¿Qué es ISO 9001?\nOtra cosa").runnable(), "eso", turnos) == "¿Qué es ISO 9001?"
    assert tutor.reformular_pregunta(LLMFalso("lo que sea").runnable(), "¿Qué es ISO 9001?", []) == "¿Qué es ISO 9001?"


def test_preambulo_de_cortesia_se_elimina(tutor_rag, llms):
    llms["llm"].respuesta = "¡Excelente pregunta! La calidad se mide con métricas."
    assert tutor_rag.get_answer("¿Qué es la calidad?")["response"] == "La calidad se mide con métricas."


def test_cita_inventada_se_reintenta_avisando_al_llm(tutor_rag, llms):
    llms["llm"].respuesta = ["Según la ISO 99999 la calidad se mide. ¿Y tú?", "Según ISO 9001 la calidad se mide. ¿Y tú?"]
    r = tutor_rag.get_answer("¿Qué es la calidad?")
    assert r["response"] == "Según ISO 9001 la calidad se mide. ¿Y tú?"
    assert llms["llm"].llamadas == 2
    assert "ATENCIÓN" in llms["llm"].prompts[1] and "ISO 99999" in llms["llm"].prompts[1]


def test_si_el_llm_insiste_en_la_cita_inventada_se_quita_esa_oracion(tutor_rag, llms):
    llms["llm"].respuesta = ["La calidad se mide. La ISO 99999 lo exige. ¿Conviene medir?"]
    r = tutor_rag.get_answer("¿Qué es la calidad?")
    assert r["response"] == "La calidad se mide. ¿Conviene medir?"
    assert llms["llm"].llamadas == 2


# ---------------------------------------------------------------- endpoint

def test_endpoint_devuelve_y_reutiliza_conversation_id(tutor_rag, llms, monkeypatch):
    monkeypatch.setattr(rag_module, "_instancia", tutor_rag)   # evita crear el RAG real al importar chat
    import app.api.v1.endpoints.chat as chat_module
    monkeypatch.setattr(chat_module, "rag_service", tutor_rag)  # chat.py lo fija al importarse
    router = chat_module.router
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    cliente = TestClient(app)

    primero = cliente.post("/api/v1/chat", json={"message": "¿Qué es la calidad del software?"}).json()
    cid = primero["conversation_id"]
    assert len(cid) >= 16, "si el cliente no envía id, el servidor genera uno"

    llms["llm"].respuesta = "Desarrollo con ejemplo."
    segundo = cliente.post("/api/v1/chat", json={"message": "Explícame eso mejor", "conversation_id": cid}).json()
    assert segundo["conversation_id"] == cid and segundo["response"] == "Desarrollo con ejemplo."
    assert "Estudiante: ¿Qué es la calidad del software?" in llms["llm"].prompts[-1]
    assert cliente.post("/api/v1/chat", json={"message": "x", "conversation_id": "a" * 101}).status_code == 422


# ---------------------------------------------------------------- salvaguardas de la respuesta

def test_puntual_sin_pregunta_final_recibe_una_pregunta_de_reflexion_generada(tutor_rag, llms):
    llms["llm"].respuesta = ["La calidad se mide con métricas.", "¿Qué métrica usarías en tu proyecto?"]
    r = tutor_rag.get_answer("¿Qué es la calidad?")
    assert r["response"] == "La calidad se mide con métricas. ¿Qué métrica usarías en tu proyecto?"
    assert "La calidad se mide con métricas." in llms["llm"].prompts[-1], "la pregunta se redacta sobre la respuesta"


def test_terminar_con_pregunta_no_toca_lo_que_ya_termina_en_pregunta_ni_agrega_basura():
    assert tutor.terminar_con_pregunta(LLMFalso("x").runnable(), "Listo. ¿Ves?") == "Listo. ¿Ves?"
    assert tutor.terminar_con_pregunta(LLMFalso("no es pregunta").runnable(), "Listo.") == "Listo."
    assert tutor.terminar_con_pregunta(LLMFalso(RuntimeError("x")).runnable(), "Listo.") == "Listo."
    assert tutor.terminar_con_pregunta(LLMFalso("¿Y tú?\notra línea").runnable(), "Listo.") == "Listo. ¿Y tú?"


def test_solo_las_puntuales_reciben_pregunta_agregada(tutor_rag, llms):
    llms["llm"].respuesta = GUIA_NUMERADA
    tutor_rag.get_answer("Resuélveme el ejercicio de auditoría")
    assert llms["llm"].llamadas == 1


@pytest.mark.parametrize("texto,esperado", [
    ("Una oración completa que es bastante larga y explica algo. Otra que se corta a la mit",
     "Una oración completa que es bastante larga y explica algo."),
    ("Termina bien.", "Termina bien."),
    ("¿Termina con pregunta?", "¿Termina con pregunta?"),
    ("sin ningún punto y se corta", "sin ningún punto y se corta"),          # nada que recortar
    ("Corta. y luego una cola muy larga que supera la mitad del texto completo sin cerrar", "Corta. y luego una cola muy larga que supera la mitad del texto completo sin cerrar"),
])
def test_recortar_a_oracion_completa(texto, esperado):
    from app.services.tutor_service import recortar_a_oracion_completa
    assert recortar_a_oracion_completa(texto) == esperado


def test_tarea_demasiado_corta_se_reintenta_con_guia_por_pasos(tutor_rag, llms):
    llms["llm"].respuesta = ["No puedo cumplir con esa solicitud.", GUIA_NUMERADA]
    r = tutor_rag.get_answer("Redáctame el plan de auditoría, dame todo resuelto")
    assert r["response"] == GUIA_NUMERADA and llms["llm"].llamadas == 2
    assert "ATENCIÓN: tu borrador fue demasiado corto o se negó" in llms["llm"].prompts[1]


def test_tarea_suficientemente_larga_no_se_reintenta(tutor_rag, llms):
    llms["llm"].respuesta = GUIA_NUMERADA
    tutor_rag.get_answer("Redáctame el plan de auditoría, dame todo resuelto")
    assert llms["llm"].llamadas == 1


def test_contexto_debil_avisa_al_llm_que_no_lo_explique_de_memoria(tutor_rag, llms, monkeypatch):
    monkeypatch.setattr(settings, "UMBRAL_RESPALDO", 2.0)    # toda recuperación cuenta como débil
    tutor_rag.get_answer("¿Qué es un plan de calidad?")
    assert "AVISO: la búsqueda no encontró" in _ultimo_prompt(llms)
    monkeypatch.setattr(settings, "UMBRAL_RESPALDO", -1.0)
    tutor_rag.get_answer("¿Qué es un plan de calidad otra vez?")
    assert "AVISO: la búsqueda no encontró" not in _ultimo_prompt(llms)


@pytest.mark.parametrize("pregunta,faltantes", [
    ("¿Qué es Scrum y cuáles son sus roles?", ["Scrum"]),
    ("¿Qué dice la ISO/IEC/IEEE 29119 sobre los niveles de prueba?", ["29119"]),
    ("¿Qué es CI/CD y por qué importa?", ["CI/CD"]),
    ("¿Qué son las métricas DORA de DevOps?", ["DORA", "DevOps"]),
    ("¿Qué es Kanban?", ["Kanban"]),
    ("¿Cómo se relaciona ISO 9001 con Scrum?", ["Scrum"]),
    ("¿Qué es la mejora continua en la ISO 9001?", []),
    ("Hola Carlos, ¿qué es un SGSI?", []),                  # nombres propios ajenos al sílabo no cuentan
    ("¿Cuántas cláusulas tiene la ISO 9001?", []),           # '9001' sí está; '8' es muy corto para contar
    ("Métricas de calidad ISO 25010", []),                   # palabra inicial en mayúscula no cuenta
    ("¿Qué dice ISO/IEC/IEEE sobre la calidad?", []),        # 'ISO/IEC/IEEE' solo no es un término
])
def test_terminos_sin_respaldo(pregunta, faltantes):
    from app.core.silabo import texto_silabo
    base = "[Documento: ISO_9001] ISO 9001 Gestión de la Calidad SGSI ISO/IEC 25010 iso_9001 Contenido"
    assert tutor.terminos_sin_respaldo(pregunta, base, texto_silabo()) == faltantes


def test_termino_ausente_activa_la_respuesta_sin_contexto_y_no_explica_el_tema(tutor_rag, llms):
    llms["llm"].respuesta = "Scrum no aparece en mis documentos; mira la Unidad 1. ¿Qué parte de calidad quieres ver?"
    r = tutor_rag.get_answer("¿Qué es Scrum y cuáles son sus roles?", conversation_id="c1")
    assert r["tipo"] == "sin_contexto" and r["response"].startswith("Scrum no aparece")
    prompt = llms["llm"].prompts[-1]
    assert "NO aparece en los documentos" in prompt and "Lo que no aparece en los documentos: Scrum" in prompt
    assert "Unidad 1:" in prompt and "iso_9001" in prompt
    assert "MODO DE ESTA RESPUESTA" not in prompt, "no se usa el prompt de explicación"
    assert llms["llm"].llamadas == 1
    assert tutor_rag.memoria.obtener("c1")[0].tipo == "sin_contexto"


@pytest.mark.parametrize("termino,unidad", [
    ("Scrum", "Unidad 1"), ("29119", "Unidad 4"), ("CI/CD", "Unidad 4"), ("DORA", "Unidad 3"), ("CMMI", "Unidad 2"),
])
def test_ubicar_en_silabo_da_la_unidad_real(termino, unidad):
    from app.core.silabo import ubicar_en_silabo
    assert any(u.startswith(unidad) for u in ubicar_en_silabo(termino))
    assert ubicar_en_silabo("Blockchain") == []


def test_sin_contexto_lleva_la_ubicacion_real_en_el_silabo(tutor_rag, llms):
    tutor_rag.get_answer("¿Qué dice la ISO/IEC/IEEE 29119 sobre los niveles de prueba?")
    prompt = llms["llm"].prompts[-1]
    from app.core.silabo import temas
    por_id = {t.id: t for t in temas()}
    pruebas = por_id["4.1"]
    assert f"Unidad 4 ({pruebas.unidad_titulo}): {pruebas.nombre}" in prompt
    tutor_rag.get_answer("¿Qué es Blockchain aplicado a ISO 9001? Explícame CMMI o SIGLAXYZ")
    madurez = por_id["2.4"]
    assert f"Unidad 2 ({madurez.unidad_titulo}): {madurez.nombre}" in llms["llm"].prompts[-1]
    tutor_rag.get_answer("¿Qué significa SIGLAXYZ?")
    assert "(el temario tampoco lo menciona)" in llms["llm"].prompts[-1]


def test_un_termino_presente_en_los_documentos_no_activa_la_ruta_sin_contexto(tutor_rag, llms):
    assert tutor_rag.get_answer("¿Qué dice la ISO 9001 sobre la calidad?")["tipo"] == "respuesta"


@pytest.mark.parametrize("texto,esperado", [
    ("Según [Documento: ISO_9001 — «ISO 9001 — Calidad»] la mejora es continua.", "Según «ISO 9001 — Calidad» la mejora es continua."),
    ("(ver [Documento: ISO_9001])", "(ver «ISO_9001»)"),
    ("Sin etiqueta.", "Sin etiqueta."),
])
def test_limpiar_etiquetas_documento(texto, esperado):
    assert tutor.limpiar_etiquetas_documento(texto) == esperado


@pytest.mark.parametrize("texto,esperado", [
    ("1. Define el alcance.\n2. Identifica riesgos.", True), ("Paso 1: define el alcance", True),
    ("Primero, define el alcance y luego lo revisamos", True), ("- define el alcance\n- revisa", True),
    ("Es importante entender qué es una auditoría. ¿Qué opinas?", False),
])
def test_tiene_pasos(texto, esperado):
    assert tutor.tiene_pasos(texto) is esperado


def test_tarea_sin_pasos_se_reintenta_una_vez(tutor_rag, llms):
    sin_pasos = "Es importante entender qué requiere una auditoría interna en tu proyecto. " * 8
    llms["llm"].respuesta = [sin_pasos, GUIA_NUMERADA]
    r = tutor_rag.get_answer("Redáctame el plan de auditoría, dame todo resuelto")
    assert r["response"] == GUIA_NUMERADA and llms["llm"].llamadas == 2
    assert "lista numerada de 4 o 5 pasos" in llms["llm"].prompts[1]


def test_una_tarea_con_solo_un_paso_tambien_se_reintenta(tutor_rag, llms):
    un_paso = "1. Identifica los activos críticos de tu proyecto. " + "Piensa en qué pasaría si fallaran. " * 8
    llms["llm"].respuesta = [un_paso, GUIA_NUMERADA]
    assert tutor_rag.get_answer("Redáctame el plan de auditoría, dame todo resuelto")["response"] == GUIA_NUMERADA


def test_tarea_reintenta_como_maximo_dos_veces(tutor_rag, llms):
    mala = "Es importante entender qué requiere una auditoría interna en tu proyecto de software. " * 6
    llms["llm"].respuesta = [mala]                     # siempre igual: nunca llega a 3 pasos
    tutor_rag.get_answer("Redáctame el plan de auditoría, dame todo resuelto")
    assert llms["llm"].llamadas == 3                   # el intento inicial + 2 reintentos
    assert llms["llm"].prompts[2].count("tu borrador fue demasiado corto") == 1


@pytest.mark.parametrize("respuesta,respaldo,invalidas", [
    ("La ISO 9001 tiene 10 cláusulas.", "ISO 9001: sigue la Estructura de Alto Nivel de diez cláusulas:", []),
    ("La norma tiene 7 cláusulas.", "Sigue la Estructura de Alto Nivel de diez cláusulas:", ["7 cláusulas"]),
    ("Son 4 dominios.", "se agrupan en cuatro dominios", []),
    ("Son 5 dominios.", "se agrupan en cuatro dominios", ["5 dominios"]),
])
def test_los_numeros_escritos_con_letras_respaldan_las_cifras(respuesta, respaldo, invalidas):
    assert tutor.normas_no_respaldadas(respuesta, respaldo) == invalidas


@pytest.mark.parametrize("respuesta,respaldo,invalidas", [
    # una cantidad escrita con letras que el contexto no trae es tan inventada como una en cifras
    ("ISO/IEC 12207 define tres niveles de madurez.", "ISO/IEC 12207 define los procesos del ciclo de vida", ["tres niveles"]),
    ("Son dos fases.", "se dividen en cuatro fases", ["dos fases"]),
    ("Hay tres niveles.", "se agrupan en tres niveles de capacidad", []),      # el contexto lo dice con letras
    ("Hay tres niveles.", "hay 3 niveles de capacidad", []),                    # ...o en cifras
    ("Hay 3 niveles.", "se agrupan en tres niveles de capacidad", []),
    ("Se usa un proceso sencillo y una fase corta.", "sin cifras", []),         # "un/una" no se controlan
    ("Tiene ocho principios y diez categorías.", "sin cifras", ["ocho principios", "diez categorías"]),
])
def test_las_cantidades_en_letras_tambien_se_verifican(respuesta, respaldo, invalidas):
    assert tutor.normas_no_respaldadas(respuesta, respaldo) == invalidas


def test_una_oracion_con_una_cantidad_inventada_en_letras_se_elimina():
    texto = "Define los procesos. Define tres niveles de madurez: madera, pino y roble. Sirve para planificar."
    invalidas = tutor.normas_no_respaldadas(texto, "define los procesos del ciclo de vida")
    assert tutor.quitar_oraciones_con(texto, invalidas) == "Define los procesos. Sirve para planificar."


def test_numero_de_pasos():
    assert tutor.numero_de_pasos(GUIA_NUMERADA) == 4
    assert tutor.numero_de_pasos("1) uno" + NL + "2) dos" + NL + "**3. tres**") == 3
    assert tutor.numero_de_pasos("Paso 1: no cuenta como lista numerada") == 0


def test_normas_y_tecnicas_no_salidas_del_contexto_se_reintentan(tutor_rag, llms):
    """Un LLM pequeño mezcla normas o técnicas 'relacionadas' que no están en el contexto recuperado."""
    llms["llm"].respuesta = ["Usa Scrum o Kanban con ISO/IEC 42010 para mejorar. ¿Y tú?", "La calidad se mide. ¿Y tú?"]
    r = tutor_rag.get_answer("¿Qué es la calidad?")
    assert r["response"] == "La calidad se mide. ¿Y tú?" and llms["llm"].llamadas == 2
    aviso = llms["llm"].prompts[1]
    assert "ATENCIÓN: en un borrador mencionaste" in aviso and "Scrum" in aviso and "42010" in aviso


def test_el_prompt_pide_nombrar_el_documento_fuente(tutor_rag, llms):
    tutor_rag.get_answer("¿Qué es la calidad?")
    assert "el documento de la base del que sale lo que explicas («ISO 9001 — Calidad»)" in _ultimo_prompt(llms)


def test_la_etiqueta_de_documento_pegada_por_el_llm_se_limpia(tutor_rag, llms):
    llms["llm"].respuesta = "Según [Documento: iso_9001 — «ISO 9001 — Calidad»] se mide. ¿Cómo?"
    assert tutor_rag.get_answer("¿Qué es la calidad?")["response"] == "Según «ISO 9001 — Calidad» se mide. ¿Cómo?"


def test_el_prompt_termina_con_el_recordatorio_del_modo(tutor_rag, llms):
    tutor_rag.get_answer("Resuélveme el ejercicio de auditoría")
    prompt = _ultimo_prompt(llms)
    assert "RECUERDA: no des la tarea resuelta" in prompt
    assert prompt.rstrip().endswith("Respuesta del tutor:")
    assert "ISO/IEC 25010 ..." not in prompt, "no debe quedar un ejemplo de cita que el modelo pueda copiar"
