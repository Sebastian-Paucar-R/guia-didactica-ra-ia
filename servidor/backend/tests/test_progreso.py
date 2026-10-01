"""Progreso de la app (XP, racha, lecciones, ejercicios): services/progreso_service.py + el router
api/v1/endpoints/progreso.py."""
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import usuario_actual
from app.services.progreso_service import ProgresoService
from tests.conftest import sembrar_usuario, usuario_de_prueba


def _hoy_utc() -> str:
    """Mismo reloj que usa el servicio (`progreso_service._hoy`, UTC): `date.today()` es la fecha LOCAL y puede
    diferir de la UTC cerca de medianoche, lo que estos tests no deben depender de la zona horaria de la máquina."""
    return datetime.now(timezone.utc).date().isoformat()


@pytest.fixture
def servicio(db_session_factory):
    sembrar_usuario(db_session_factory, "ana")
    return ProgresoService(db_session_factory)


# ---------------------------------------------------------------- servicio: XP y racha

def test_estudiante_sin_progreso_tiene_estado_inicial(servicio):
    datos = servicio.obtener("nadie-todavia")
    assert datos == {"uid": "nadie-todavia", "xp_total": 0, "racha_actual": 0, "racha_mejor": 0,
                     "ultima_actividad_fecha": None, "lecciones_completadas": 0, "ejercicios_resueltos": 0,
                     "ejercicios_correctos": 0}


def test_completar_leccion_suma_xp_y_abre_la_racha(servicio):
    d = servicio.completar_leccion("ana", "leccion-iso-9001")
    assert d["lecciones_completadas"] == 1 and d["xp_total"] == 20 and d["racha_actual"] == 1
    assert d["ultima_actividad_fecha"] == _hoy_utc()


def test_resolver_ejercicio_correcto_da_mas_xp_que_incorrecto(servicio):
    correcto = servicio.resolver_ejercicio("ana", "ej-1", correcto=True)
    assert correcto["xp_total"] == 10 and correcto["ejercicios_resueltos"] == 1 and correcto["ejercicios_correctos"] == 1

    d = servicio.resolver_ejercicio("ana", "ej-2", correcto=False)
    assert d["xp_total"] == 10 + 2 and d["ejercicios_resueltos"] == 2 and d["ejercicios_correctos"] == 1


def test_dos_eventos_el_mismo_dia_no_duplican_la_racha(servicio):
    servicio.completar_leccion("ana", "leccion-iso-9001")
    d = servicio.resolver_ejercicio("ana", "ej-1", correcto=True)
    assert d["racha_actual"] == 1   # sigue en 1: mismo día, no sube dos veces


def test_racha_sube_con_actividad_en_dias_consecutivos(servicio, monkeypatch):
    import app.services.progreso_service as mod
    ayer = (datetime.now(timezone.utc).date() - timedelta(days=1)).isoformat()
    monkeypatch.setattr(mod, "_hoy", lambda: ayer)
    servicio.completar_leccion("ana", "leccion-iso-9001")
    monkeypatch.undo()
    d = servicio.completar_leccion("ana", "leccion-iso-25010")
    assert d["racha_actual"] == 2 and d["racha_mejor"] == 2


def test_racha_se_reinicia_tras_un_hueco_de_mas_de_un_dia(servicio, monkeypatch):
    import app.services.progreso_service as mod
    hace_tres_dias = (datetime.now(timezone.utc).date() - timedelta(days=3)).isoformat()
    monkeypatch.setattr(mod, "_hoy", lambda: hace_tres_dias)
    servicio.completar_leccion("ana", "leccion-iso-9001")
    monkeypatch.undo()
    d = servicio.completar_leccion("ana", "leccion-iso-25010")
    assert d["racha_actual"] == 1 and d["racha_mejor"] == 1   # la mejor de antes no bajó porque ya era 1


# ---------------------------------------------------------------- endpoints

@pytest.fixture
def cliente(db_session_factory):
    sembrar_usuario(db_session_factory, "u-progreso")
    import app.api.v1.endpoints.progreso as progreso_module
    app = FastAPI()
    app.include_router(progreso_module.router, prefix="/api/v1")
    app.dependency_overrides[usuario_actual] = lambda: usuario_de_prueba("u-progreso")
    # session_factory_por_defecto() es un singleton perezoso (una vez por proceso): sin esto, el primer test del
    # proceso que lo toque lo fija a SU DATABASE_URL temporal, y los demás (distinto tmp_path) escribirían contra
    # una base ajena. Se sustituye igual que api/v1/endpoints/usuarios.py hace con get_db.
    app.dependency_overrides[progreso_module._servicio] = lambda: ProgresoService(db_session_factory)
    return TestClient(app)


def test_endpoint_mi_progreso_inicial(cliente):
    r = cliente.get("/api/v1/progreso/mio")
    assert r.status_code == 200 and r.json()["xp_total"] == 0


def test_endpoint_completar_leccion_y_resolver_ejercicio(cliente):
    r1 = cliente.post("/api/v1/progreso/lecciones/leccion-iso-9001/completar")
    assert r1.status_code == 200 and r1.json()["lecciones_completadas"] == 1

    r2 = cliente.post("/api/v1/progreso/ejercicios/ej-1/resolver", json={"correcto": True, "leccion_id": "leccion-iso-9001"})
    assert r2.status_code == 200
    assert r2.json()["ejercicios_resueltos"] == 1 and r2.json()["ejercicios_correctos"] == 1
    assert r2.json()["xp_total"] == 20 + 10

    r3 = cliente.get("/api/v1/progreso/mio")
    assert r3.json()["xp_total"] == 30
