"""Historial de conversaciones (app/services/historial_service.py, endpoints GET /historial/...)."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import usuario_actual
from app.api.v1.endpoints.historial import router
from app.services.historial_service import HistorialService
from tests.conftest import sembrar_usuario, usuario_de_prueba


# ---------------------------------------------------------------- servicio

def test_registrar_turno_crea_la_conversacion_la_primera_vez(db_session_factory):
    sembrar_usuario(db_session_factory, "ana")
    h = HistorialService(db_session_factory)
    h.registrar_turno("ana", "c1", "¿Qué es ISO 9001?", "Es una norma...", "respuesta",
                      tema_detectado="2.2", unidad_detectada=2)
    convs = h.conversaciones_de("ana")
    assert len(convs) == 1 and convs[0]["id"] == "c1" and convs[0]["titulo"] == "¿Qué es ISO 9001?"


def test_dos_turnos_en_la_misma_conversacion_no_la_duplican(db_session_factory):
    sembrar_usuario(db_session_factory, "ana")
    h = HistorialService(db_session_factory)
    h.registrar_turno("ana", "c1", "¿Qué es ISO 9001?", "...", "respuesta")
    h.registrar_turno("ana", "c1", "Explícame mejor", "...", "respuesta")
    assert len(h.conversaciones_de("ana")) == 1
    assert len(h.mensajes_de("ana", "c1")) == 4   # 2 turnos x (estudiante + tutor)


def test_cada_turno_agrega_un_mensaje_de_cada_rol_en_orden(db_session_factory):
    sembrar_usuario(db_session_factory, "ana")
    h = HistorialService(db_session_factory)
    h.registrar_turno("ana", "c1", "¿Qué es ISO 9001?", "Es una norma de calidad.", "respuesta", desde_cache=True,
                      latencia_ms=12.5)
    m = h.mensajes_de("ana", "c1")
    assert [x["rol"] for x in m] == ["estudiante", "tutor"]
    assert m[0]["contenido"] == "¿Qué es ISO 9001?" and m[1]["contenido"] == "Es una norma de calidad."
    assert m[1]["tipo"] == "respuesta"


def test_conversaciones_de_devuelve_mas_reciente_primero(db_session_factory):
    sembrar_usuario(db_session_factory, "ana")
    h = HistorialService(db_session_factory, reloj=iter(
        ["2026-01-01T00:00:00+00:00", "2026-02-01T00:00:00+00:00"]).__next__)   # un valor por registrar_turno
    h.registrar_turno("ana", "vieja", "primero", "...", "respuesta")
    h.registrar_turno("ana", "nueva", "segundo", "...", "respuesta")
    assert [c["id"] for c in h.conversaciones_de("ana")] == ["nueva", "vieja"]


def test_mensajes_de_conversacion_ajena_devuelve_none(db_session_factory):
    sembrar_usuario(db_session_factory, "ana")
    sembrar_usuario(db_session_factory, "beto")
    h = HistorialService(db_session_factory)
    h.registrar_turno("ana", "c1", "¿Qué es ISO 9001?", "...", "respuesta")
    assert h.mensajes_de("beto", "c1") is None
    assert h.mensajes_de("ana", "no-existe") is None


# ---------------------------------------------------------------- endpoints

@pytest.fixture
def cliente(db_session_factory):
    from app.services.rag_service import RAGService, get_rag_service
    sembrar_usuario(db_session_factory, "ana")
    sembrar_usuario(db_session_factory, "beto")
    historial = HistorialService(db_session_factory)
    historial.registrar_turno("ana", "c1", "¿Qué es ISO 9001?", "Es una norma.", "respuesta")
    historial.registrar_turno("beto", "c2", "¿Qué es Scrum?", "Es un marco ágil.", "respuesta")

    class RagFalso:
        pass
    rag = RagFalso()
    rag.historial = historial

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_rag_service] = lambda: rag
    app.dependency_overrides[usuario_actual] = lambda: usuario_de_prueba("ana")
    return TestClient(app)


def test_mis_conversaciones_solo_trae_las_propias(cliente):
    r = cliente.get("/api/v1/historial/conversaciones")
    assert r.status_code == 200
    ids = [c["id"] for c in r.json()]
    assert ids == ["c1"]   # no "c2", que es de beto


def test_mensajes_de_mi_conversacion(cliente):
    r = cliente.get("/api/v1/historial/conversaciones/c1/mensajes")
    assert r.status_code == 200
    assert [m["rol"] for m in r.json()] == ["estudiante", "tutor"]


def test_mensajes_de_conversacion_ajena_es_404(cliente):
    assert cliente.get("/api/v1/historial/conversaciones/c2/mensajes").status_code == 404


def test_sin_autenticar_es_401(db_session_factory):
    from app.services.rag_service import get_rag_service
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    assert TestClient(app).get("/api/v1/historial/conversaciones").status_code == 401
