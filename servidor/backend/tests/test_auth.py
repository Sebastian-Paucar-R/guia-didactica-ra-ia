"""Identidad (Firebase Authentication), consentimiento informado y roles: app/api/deps.py.

`verificar_token` (app/core/firebase_auth.py) se sustituye directamente en cada test, como el resto del proyecto
sustituye el LLM o los embeddings: no hace falta credencial real de Firebase ni red para probar la lógica de la
app (crear el usuario la primera vez, actualizar el acceso, exigir consentimiento, exigir rol)."""
import pytest
from fastapi import Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.api import deps
from app.core import firebase_auth
from app.db.base import Base
from app.db.models import Usuario
from app.db.session import crear_engine, crear_sessionmaker, get_db


@pytest.fixture
def app_y_sesion(tmp_path):
    url = f"sqlite:///{(tmp_path / 't.db').as_posix()}"
    engine = crear_engine(url)
    Base.metadata.create_all(engine)
    fabrica = crear_sessionmaker(engine)

    app = FastAPI()
    app.dependency_overrides[get_db] = lambda: fabrica()

    @app.get("/quien-soy")
    def quien_soy(usuario: Usuario = Depends(deps.usuario_actual)):
        return {"uid": usuario.uid_firebase, "rol": usuario.rol, "correo": usuario.correo}

    @app.get("/con-consentimiento")
    def con_consentimiento(usuario: Usuario = Depends(deps.usuario_con_consentimiento)):
        return {"uid": usuario.uid_firebase}

    @app.get("/solo-docente")
    def solo_docente(usuario: Usuario = Depends(deps.requiere_rol("docente", "admin"))):
        return {"uid": usuario.uid_firebase}

    return TestClient(app), fabrica


def _claims(uid="uid-1", email="ana@example.com", name="Ana", picture="http://x/p.png", proveedor="google.com"):
    return {"uid": uid, "email": email, "name": name, "picture": picture, "firebase": {"sign_in_provider": proveedor}}


# ---------------------------------------------------------------- usuario_actual

def test_sin_encabezado_es_401(app_y_sesion):
    http, _ = app_y_sesion
    assert http.get("/quien-soy").status_code == 401


def test_encabezado_sin_bearer_es_401(app_y_sesion):
    http, _ = app_y_sesion
    assert http.get("/quien-soy", headers={"Authorization": "Basic abc"}).status_code == 401


def test_token_invalido_es_401(app_y_sesion, monkeypatch):
    http, _ = app_y_sesion
    monkeypatch.setattr(firebase_auth, "verificar_token",
                        lambda t: (_ for _ in ()).throw(ValueError("token expirado")))
    r = http.get("/quien-soy", headers={"Authorization": "Bearer x"})
    assert r.status_code == 401 and "token" in r.json()["detail"].lower()


def test_primera_vez_crea_el_usuario_con_rol_estudiante(app_y_sesion, monkeypatch):
    http, fabrica = app_y_sesion
    monkeypatch.setattr(firebase_auth, "verificar_token", lambda t: _claims())
    r = http.get("/quien-soy", headers={"Authorization": "Bearer x"})
    assert r.status_code == 200
    assert r.json() == {"uid": "uid-1", "rol": "estudiante", "correo": "ana@example.com"}
    with fabrica() as ses:
        u = ses.get(Usuario, "uid-1")
        assert u.nombre == "Ana" and u.proveedor == "google" and u.consentimiento_aceptado is False
        assert u.fecha_registro and u.ultimo_acceso


def test_proveedor_password_se_guarda_como_password(app_y_sesion, monkeypatch):
    http, fabrica = app_y_sesion
    monkeypatch.setattr(firebase_auth, "verificar_token", lambda t: _claims(proveedor="password"))
    http.get("/quien-soy", headers={"Authorization": "Bearer x"})
    with fabrica() as ses:
        assert ses.get(Usuario, "uid-1").proveedor == "password"


def test_segunda_vez_actualiza_ultimo_acceso_y_conserva_rol(app_y_sesion, monkeypatch):
    http, fabrica = app_y_sesion
    monkeypatch.setattr(firebase_auth, "verificar_token", lambda t: _claims())
    http.get("/quien-soy", headers={"Authorization": "Bearer x"})
    with fabrica() as ses:
        u = ses.get(Usuario, "uid-1")
        u.rol = "docente"                      # un ascenso a docente no lo toca Firebase
        primer_acceso = u.ultimo_acceso
        ses.commit()

    monkeypatch.setattr(firebase_auth, "verificar_token", lambda t: _claims(name="Ana María"))
    r = http.get("/quien-soy", headers={"Authorization": "Bearer x"})
    assert r.json()["rol"] == "docente"        # el rol es de la app, Firebase no lo cambia
    with fabrica() as ses:
        u = ses.get(Usuario, "uid-1")
        assert u.nombre == "Ana María"          # lo que Firebase sí trae se refresca
        assert u.ultimo_acceso >= primer_acceso


def test_sin_uid_en_el_token_es_401(app_y_sesion, monkeypatch):
    http, _ = app_y_sesion
    monkeypatch.setattr(firebase_auth, "verificar_token", lambda t: {"email": "x@x.com"})
    assert http.get("/quien-soy", headers={"Authorization": "Bearer x"}).status_code == 401


# ---------------------------------------------------------------- consentimiento

def test_sin_consentimiento_es_409(app_y_sesion, monkeypatch):
    http, _ = app_y_sesion
    monkeypatch.setattr(firebase_auth, "verificar_token", lambda t: _claims())
    r = http.get("/con-consentimiento", headers={"Authorization": "Bearer x"})
    assert r.status_code == 409 and "consentimiento" in r.json()["detail"].lower()


def test_con_consentimiento_pasa(app_y_sesion, monkeypatch):
    http, fabrica = app_y_sesion
    with fabrica() as ses:
        ses.add(Usuario(uid_firebase="uid-1", correo="a@a.com", nombre="Ana", proveedor="password", rol="estudiante",
                        fecha_registro="2026-01-01T00:00:00+00:00", ultimo_acceso="2026-01-01T00:00:00+00:00",
                        consentimiento_aceptado=True, consentimiento_fecha="2026-01-01T00:00:00+00:00"))
        ses.commit()
    monkeypatch.setattr(firebase_auth, "verificar_token", lambda t: _claims())
    assert http.get("/con-consentimiento", headers={"Authorization": "Bearer x"}).status_code == 200


# ---------------------------------------------------------------- roles

def test_requiere_rol_devuelve_403_si_no_coincide(app_y_sesion, monkeypatch):
    http, _ = app_y_sesion
    monkeypatch.setattr(firebase_auth, "verificar_token", lambda t: _claims())   # estudiante por defecto
    assert http.get("/solo-docente", headers={"Authorization": "Bearer x"}).status_code == 403


def test_requiere_rol_deja_pasar_al_rol_correcto(app_y_sesion, monkeypatch):
    http, fabrica = app_y_sesion
    monkeypatch.setattr(firebase_auth, "verificar_token", lambda t: _claims())
    http.get("/quien-soy", headers={"Authorization": "Bearer x"})   # crea el usuario
    with fabrica() as ses:
        ses.get(Usuario, "uid-1").rol = "docente"
        ses.commit()
    assert http.get("/solo-docente", headers={"Authorization": "Bearer x"}).status_code == 200


# ---------------------------------------------------------------- verificar_propietario

def _usuario(uid, rol="estudiante"):
    return Usuario(uid_firebase=uid, correo=f"{uid}@x.com", nombre=uid, proveedor="password", rol=rol,
                  fecha_registro="2026-01-01T00:00:00+00:00", ultimo_acceso="2026-01-01T00:00:00+00:00",
                  consentimiento_aceptado=True)


def test_verificar_propietario_deja_pasar_al_dueno():
    deps.verificar_propietario(_usuario("ana"), "ana")   # no lanza


def test_verificar_propietario_rechaza_a_otro_estudiante():
    with pytest.raises(HTTPException) as exc:
        deps.verificar_propietario(_usuario("ana"), "beto")
    assert exc.value.status_code == 403


def test_verificar_propietario_deja_pasar_a_docente_y_admin():
    for rol in ("docente", "admin"):
        deps.verificar_propietario(_usuario("prof1", rol=rol), "cualquier-estudiante")   # no lanza
