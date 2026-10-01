"""Estadísticas docentes (app/api/v1/endpoints/docente.py): agregados, nunca datos de un estudiante concreto."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import usuario_actual
from app.api.v1.endpoints.docente import router
from app.db.models import Mensaje
from app.db.session import get_db
from app.models.perfil import PerfilEstudiante
from app.services.historial_service import HistorialService
from app.services.perfil_service import PerfilService
from tests.conftest import sembrar_usuario, usuario_de_prueba


@pytest.fixture
def escenario(db_session_factory):
    """Dos estudiantes activos: "ana" (nivel bajo en la unidad 2, con dificultad en 2.2) y "beto" (neutro).
    Un tercero, "gastón", sin actividad reciente (para estudiantes_activos)."""
    for uid in ("ana", "beto", "gaston"):
        sembrar_usuario(db_session_factory, uid)
    perfiles = PerfilService(db_session_factory)
    perfiles.guardar(PerfilEstudiante(user_id="ana", nivel_por_unidad={2: 1.8}, temas_con_dificultad=["2.2"]))
    perfiles.guardar(PerfilEstudiante(user_id="beto", nivel_por_unidad={2: 4.6}))
    historial = HistorialService(db_session_factory)
    historial.registrar_turno("ana", "c1", "¿Qué es ISO 9001?", "...", "respuesta", unidad_detectada=2, tema_detectado="2.2")
    historial.registrar_turno("ana", "c1", "Explícame mejor", "...", "respuesta", unidad_detectada=2, tema_detectado="2.2")
    historial.registrar_turno("beto", "c2", "¿Qué es Scrum?", "...", "respuesta", unidad_detectada=1, tema_detectado="1.2")
    return db_session_factory


@pytest.fixture
def cliente(db_session_factory, monkeypatch):
    from app.core import config as config_module
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: db_session_factory()
    app.dependency_overrides[usuario_actual] = lambda: usuario_de_prueba("prof1", rol="docente")
    return TestClient(app)


def test_exige_rol_docente_o_admin(db_session_factory):
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: db_session_factory()
    app.dependency_overrides[usuario_actual] = lambda: usuario_de_prueba("est1", rol="estudiante")
    assert TestClient(app).get("/api/v1/docente/estadisticas").status_code == 403


def test_sin_autenticar_es_401(db_session_factory):
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: db_session_factory()
    assert TestClient(app).get("/api/v1/docente/estadisticas").status_code == 401


def test_estudiantes_totales_y_preguntas_por_unidad(escenario, cliente):
    d = cliente.get("/api/v1/docente/estadisticas").json()
    assert d["estudiantes_totales"] == 3   # ana, beto, gaston (docente "prof1" no cuenta: no es estudiante)
    por_unidad = {p["unidad"]: p["preguntas"] for p in d["preguntas_por_unidad"]}
    assert por_unidad[1] == 1 and por_unidad[2] == 2   # ana preguntó 2 veces (unidad 2), beto 1 (unidad 1)


def test_temas_con_mas_dificultad(escenario, cliente):
    d = cliente.get("/api/v1/docente/estadisticas").json()
    assert d["temas_con_mas_dificultad"] == [{"tema_id": "2.2", "tema": "ISO 9001: sistema de gestión de la calidad",
                                              "unidad": 2, "estudiantes": 1}]


def test_evolucion_por_unidad_promedia_los_niveles(escenario, cliente):
    d = cliente.get("/api/v1/docente/estadisticas").json()
    u2 = next(u for u in d["evolucion_por_unidad"] if u["unidad"] == 2)
    # ana=1.8, beto=4.6 -> media 3.2; gastón no tiene perfil guardado, no entra en el promedio
    assert u2["nivel_medio_actual"] == 3.2 and u2["cambio_medio"] == 0.2


def test_sin_ningun_perfil_ni_mensaje_devuelve_ceros_no_error(db_session_factory, cliente):
    sembrar_usuario(db_session_factory, "solo1")
    d = cliente.get("/api/v1/docente/estadisticas").json()
    assert d["estudiantes_totales"] == 1
    assert all(u["nivel_medio_actual"] == 3.0 for u in d["evolucion_por_unidad"])
    assert d["temas_con_mas_dificultad"] == []


def test_estudiantes_activos_respeta_la_ventana_de_dias(db_session_factory, monkeypatch):
    from datetime import datetime, timedelta, timezone
    from app.db.models import Usuario
    with db_session_factory() as ses:
        hace_mucho = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat(timespec="seconds")
        ahora = datetime.now(timezone.utc).isoformat(timespec="seconds")
        ses.add(Usuario(uid_firebase="reciente", correo="r@x.com", proveedor="password", rol="estudiante",
                        fecha_registro=ahora, ultimo_acceso=ahora, consentimiento_aceptado=True))
        ses.add(Usuario(uid_firebase="viejo", correo="v@x.com", proveedor="password", rol="estudiante",
                        fecha_registro=hace_mucho, ultimo_acceso=hace_mucho, consentimiento_aceptado=True))
        ses.commit()
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: db_session_factory()
    app.dependency_overrides[usuario_actual] = lambda: usuario_de_prueba("prof1", rol="docente")
    http = TestClient(app)
    d = http.get("/api/v1/docente/estadisticas?dias_actividad_reciente=7").json()
    assert d["estudiantes_totales"] == 2 and d["estudiantes_activos"] == 1
