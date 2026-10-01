"""Consentimiento informado (POST /api/v1/usuarios/consentimiento) y GET /usuarios/yo."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.endpoints.usuarios import router
from app.core import firebase_auth
from app.db.base import Base
from app.db.session import crear_engine, crear_sessionmaker, get_db


@pytest.fixture
def cliente(tmp_path, monkeypatch):
    url = f"sqlite:///{(tmp_path / 't.db').as_posix()}"
    Base.metadata.create_all(crear_engine(url))
    fabrica = crear_sessionmaker(database_url=url)
    monkeypatch.setattr(firebase_auth, "verificar_token", lambda t: {
        "uid": "uid-1", "email": "ana@example.com", "name": "Ana",
        "firebase": {"sign_in_provider": "password"}})
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    app.dependency_overrides[get_db] = lambda: fabrica()
    return TestClient(app)


def _bearer():
    return {"Authorization": "Bearer x"}


def test_yo_crea_el_usuario_sin_consentimiento(cliente):
    r = cliente.get("/api/v1/usuarios/yo", headers=_bearer())
    assert r.status_code == 200
    d = r.json()
    assert d["uid"] == "uid-1" and d["consentimiento_aceptado"] is False and d["consentimiento_fecha"] is None
    assert d["rol"] == "estudiante"


def test_aceptar_consentimiento_lo_registra_con_fecha(cliente):
    r = cliente.post("/api/v1/usuarios/consentimiento", headers=_bearer())
    assert r.status_code == 200
    d = r.json()
    assert d["consentimiento_aceptado"] is True and d["consentimiento_fecha"]


def test_el_consentimiento_persiste_entre_peticiones(cliente):
    cliente.post("/api/v1/usuarios/consentimiento", headers=_bearer())
    d = cliente.get("/api/v1/usuarios/yo", headers=_bearer()).json()
    assert d["consentimiento_aceptado"] is True


def test_sin_autenticar_es_401(cliente):
    assert cliente.get("/api/v1/usuarios/yo").status_code == 401
    assert cliente.post("/api/v1/usuarios/consentimiento").status_code == 401
