"""Perfil del estudiante: modelo, persistencia en SQLite y endpoints /perfil."""
import sqlite3

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.api.v1.endpoints.perfil import router as perfil_router
from app.core import silabo
from app.models.perfil import (
    MAX_HISTORIAL, NIVEL_INICIAL, UNIDADES, CambioNivel, PerfilEstudiante)
from app.services.perfil_service import PerfilService
from app.services.rag_service import get_rag_service


def _perfil(**campos) -> PerfilEstudiante:
    return PerfilEstudiante(user_id="u1", **campos)


# ================================================================ modelo

def test_las_unidades_del_modelo_son_las_del_silabo():
    assert set(UNIDADES) == {u["numero"] for u in silabo.unidades()}


def test_perfil_inicial():
    p = _perfil()
    assert p.nivel_por_unidad == {1: 3.0, 2: 3.0, 3: 3.0, 4: 3.0}
    assert (p.profundidad_preferida, p.estilo_preferido) == ("media", "conceptual")
    assert p.temas_consultados == {} and p.temas_con_dificultad == [] and p.historial_resumido == []
    assert (p.ritmo.sesiones, p.ritmo.mensajes_totales, p.ritmo.duracion_media_s) == (0, 0, 0.0)
    assert p.es_neutro() and p.sintesis_historial() == ""


def test_el_nivel_se_completa_y_se_acota_entre_1_y_5():
    p = _perfil(nivel_por_unidad={1: 9, 2: -3})
    assert p.nivel_por_unidad == {1: 5.0, 2: 1.0, 3: NIVEL_INICIAL, 4: NIVEL_INICIAL}


def test_una_unidad_fuera_del_silabo_se_rechaza():
    with pytest.raises(ValidationError):
        _perfil(nivel_por_unidad={7: 3.0})


@pytest.mark.parametrize("valor", ["muy_larga", "otra", ""])
def test_profundidad_y_estilo_solo_admiten_sus_valores(valor):
    with pytest.raises(ValidationError):
        _perfil(profundidad_preferida=valor)
    with pytest.raises(ValidationError):
        _perfil(estilo_preferido=valor)


@pytest.mark.parametrize("nivel, franja", [
    (1.0, "bajo"), (2.4, "bajo"), (2.5, "medio"), (3.0, "medio"), (3.5, "medio"), (3.6, "alto"), (5.0, "alto")])
def test_franjas_de_nivel(nivel, franja):
    assert _perfil(nivel_por_unidad={2: nivel}).franja(2) == franja


def test_sin_unidad_conocida_el_nivel_es_medio():
    assert _perfil(nivel_por_unidad={2: 1.0}).franja(None) == "medio"


def test_mover_nivel_no_sale_del_rango_y_devuelve_antes_y_despues():
    p = _perfil(nivel_por_unidad={1: 1.2, 2: 4.9})
    assert p.mover_nivel(1, -0.4) == (1.2, 1.0)
    assert p.mover_nivel(2, +0.3) == (4.9, 5.0)
    assert p.nivel(1) == 1.0 and p.nivel(2) == 5.0 and p.nivel(3) == 3.0


def test_registrar_tema_cuenta_consultas_y_guarda_los_ultimos_cinco_distintos():
    p = _perfil()
    for i in range(1, 8):
        p.registrar_tema(f"1.{i}", f"Tema {i}", 1)
    assert [t.tema_id for t in p.historial_resumido] == ["1.3", "1.4", "1.5", "1.6", "1.7"]
    assert len(p.historial_resumido) == MAX_HISTORIAL
    p.registrar_tema("1.4", "Tema 4", 1)                      # ya estaba: sube al final, no se duplica
    assert [t.tema_id for t in p.historial_resumido] == ["1.3", "1.5", "1.6", "1.7", "1.4"]
    assert p.temas_consultados["1.4"] == 2 and p.temas_consultados["1.1"] == 1


def test_sintesis_del_historial_va_del_mas_reciente_al_mas_antiguo():
    p = _perfil()
    p.registrar_tema("2.2", "ISO 9001", 2)
    p.registrar_tema("1.2", "Scrum", 1)
    assert p.sintesis_historial() == "«Scrum» (Unidad 1); «ISO 9001» (Unidad 2)"


@pytest.mark.parametrize("campos", [
    {"nivel_por_unidad": {2: 2.0}}, {"nivel_por_unidad": {2: 4.0}}, {"profundidad_preferida": "extensa"},
    {"estilo_preferido": "ejemplos"}, {"temas_con_dificultad": ["2.2"]}])
def test_un_perfil_con_algo_que_ajustar_no_es_neutro(campos):
    assert not _perfil(**campos).es_neutro()


def test_el_perfil_sobrevive_a_json():
    p = _perfil(nivel_por_unidad={2: 1.8}, estilo_preferido="ejemplos")
    p.registrar_tema("2.2", "ISO 9001", 2)
    assert PerfilEstudiante.model_validate_json(p.model_dump_json()) == p


# ================================================================ persistencia

@pytest.fixture
def servicio(tmp_path):
    return PerfilService(tmp_path / "perfiles.db")


def _tocar(unidad=2, nivel_delta=0.0, tema=("2.2", "ISO 9001", 2)):
    def actualizar(p):
        p.registrar_tema(*tema)
        if nivel_delta:
            antes, despues = p.mover_nivel(unidad, nivel_delta)
            return [CambioNivel(unidad=unidad, nivel=despues, motivo="confusion", tema_id=tema[0])]
        return []
    return actualizar


def test_sin_perfil_se_devuelve_el_inicial_sin_guardarlo(servicio):
    p = servicio.obtener("nadie")
    assert p.user_id == "nadie" and p.es_neutro() and not servicio.existe("nadie")


def test_registrar_turno_guarda_y_sobrevive_a_reabrir_la_base(servicio, tmp_path):
    servicio.registrar_turno("ana", "c1", _tocar(nivel_delta=-0.4))
    otra_instancia = PerfilService(tmp_path / "perfiles.db")
    p = otra_instancia.obtener("ana")
    assert otra_instancia.existe("ana") and p.nivel(2) == 2.6
    assert p.temas_consultados == {"2.2": 1} and p.creado_en and p.actualizado_en


def test_si_la_actualizacion_falla_no_se_guarda_nada(servicio):
    def rota(p):
        p.registrar_tema("2.2", "ISO 9001", 2)
        raise RuntimeError("fallo a medias")

    with pytest.raises(RuntimeError):
        servicio.registrar_turno("ana", "c1", rota)
    assert not servicio.existe("ana")
    con = sqlite3.connect(servicio.ruta)
    try:
        assert con.execute("SELECT COUNT(*) FROM sesiones").fetchone()[0] == 0
    finally:
        con.close()


def test_los_estudiantes_no_se_mezclan(servicio):
    servicio.registrar_turno("ana", "c1", _tocar(nivel_delta=-0.4))
    servicio.registrar_turno("beto", "c2", _tocar(tema=("1.2", "Scrum", 1)))
    assert servicio.obtener("ana").nivel(2) == 2.6 and servicio.obtener("beto").nivel(2) == 3.0
    assert set(servicio.obtener("beto").temas_consultados) == {"1.2"}


def test_el_progreso_parte_de_3_y_recoge_cada_cambio_en_orden(servicio):
    for _ in range(3):
        servicio.registrar_turno("ana", "c1", _tocar(nivel_delta=-0.4))
    puntos = servicio.progreso("ana")
    assert set(puntos) == set(UNIDADES)
    assert [p["nivel"] for p in puntos[2]] == [3.0, 2.6, 2.2, 1.8]
    assert puntos[2][0]["motivo"] == "inicial" and puntos[2][1]["motivo"] == "confusion" and puntos[2][1]["tema_id"] == "2.2"
    assert [p["nivel"] for p in puntos[1]] == [3.0]           # las demás unidades no cambiaron


def test_progreso_de_quien_no_existe_solo_tiene_el_punto_inicial(servicio):
    puntos = servicio.progreso("nadie")
    assert all(len(v) == 1 and v[0]["nivel"] == 3.0 for v in puntos.values())


def test_un_turno_sin_cambio_de_nivel_no_agrega_progreso(servicio):
    servicio.registrar_turno("ana", "c1", _tocar())
    assert all(len(v) == 1 for v in servicio.progreso("ana").values())


def test_ritmo_mensajes_por_sesion_y_duracion_media(tmp_path):
    reloj = iter(["2026-09-20T10:00:00+00:00", "2026-09-20T10:10:00+00:00", "2026-09-20T10:20:00+00:00",
                  "2026-09-21T09:00:00+00:00", "2026-09-22T09:00:00+00:00"])
    servicio = PerfilService(tmp_path / "p.db", reloj=lambda: next(reloj))
    for conversacion in ("c1", "c1", "c1", "c2", "c3"):
        p = servicio.registrar_turno("ana", conversacion, _tocar())
    # c1: 3 mensajes en 20 min; c2 y c3: 1 mensaje (su duración no significa nada y no entra en la media)
    assert p.ritmo.sesiones == 3 and p.ritmo.mensajes_totales == 5
    assert p.ritmo.mensajes_por_sesion == pytest.approx(5 / 3, abs=0.01)
    assert p.ritmo.duracion_media_s == 1200.0


def test_sin_conversacion_el_mensaje_no_crea_sesion(servicio):
    p = servicio.registrar_turno("ana", None, _tocar())
    assert p.ritmo.sesiones == 0


def test_reiniciar_borra_perfil_progreso_y_sesiones(servicio):
    servicio.registrar_turno("ana", "c1", _tocar(nivel_delta=-0.4))
    servicio.registrar_turno("beto", "c2", _tocar(nivel_delta=-0.4))
    inicial = servicio.reiniciar("ana")
    assert inicial.es_neutro() and not servicio.existe("ana")
    assert all(len(v) == 1 for v in servicio.progreso("ana").values())
    con = sqlite3.connect(servicio.ruta)
    try:
        assert con.execute("SELECT COUNT(*) FROM sesiones WHERE user_id = 'ana'").fetchone()[0] == 0
    finally:
        con.close()
    assert servicio.obtener("beto").nivel(2) == 2.6            # el de otro estudiante no se toca


def test_guardar_siembra_un_perfil_tal_cual(servicio):
    servicio.guardar(_perfil(nivel_por_unidad={2: 1.8}, profundidad_preferida="extensa"))
    p = servicio.obtener("u1")
    assert p.nivel(2) == 1.8 and p.profundidad_preferida == "extensa" and p.creado_en


def test_user_id_con_comillas_no_rompe_las_consultas(servicio):
    raro = "x'; DROP TABLE perfiles; --"
    servicio.registrar_turno(raro, "c1", _tocar())
    assert servicio.existe(raro) and servicio.reiniciar(raro).user_id == raro
    assert not servicio.existe(raro)


# ================================================================ endpoints

@pytest.fixture
def cliente(rag):
    app = FastAPI()
    app.include_router(perfil_router, prefix="/api/v1")
    app.dependency_overrides[get_rag_service] = lambda: rag
    return TestClient(app), rag


def test_get_perfil_de_un_estudiante_nuevo_devuelve_el_inicial(cliente):
    http, rag = cliente
    r = http.get("/api/v1/perfil/ana")
    assert r.status_code == 200
    d = r.json()
    assert d["user_id"] == "ana" and d["es_nuevo"] is True
    assert d["nivel_por_unidad"] == {"1": 3.0, "2": 3.0, "3": 3.0, "4": 3.0}
    assert (d["profundidad_preferida"], d["estilo_preferido"]) == ("media", "conceptual")
    assert d["dificultades"] == [] and d["resumen_historial"] == ""
    assert not rag.perfiles.existe("ana"), "consultar un perfil nuevo no lo crea"


def test_get_perfil_devuelve_lo_aprendido(cliente):
    http, rag = cliente

    def actualizar(p):
        p.registrar_tema("2.2", "ISO 9001: sistema de gestión de la calidad", 2)
        p.temas_con_dificultad.append("2.2")
        p.mover_nivel(2, -0.4)
        p.estilo_preferido = "ejemplos"

    rag.perfiles.registrar_turno("ana", "c1", actualizar)
    d = http.get("/api/v1/perfil/ana").json()
    assert d["es_nuevo"] is False and d["nivel_por_unidad"]["2"] == 2.6 and d["estilo_preferido"] == "ejemplos"
    assert d["temas_consultados"] == {"2.2": 1}
    assert d["dificultades"] == [{"tema_id": "2.2", "tema": "ISO 9001: sistema de gestión de la calidad", "unidad": 2}]
    assert "ISO 9001" in d["resumen_historial"]
    assert d["ritmo"]["sesiones"] == 1 and d["ritmo"]["mensajes_totales"] == 1
    assert len(d["historial_resumido"]) == 1


def test_progreso_por_unidad_con_titulo_nivel_actual_y_puntos(cliente):
    http, rag = cliente
    for _ in range(2):
        rag.perfiles.registrar_turno("ana", "c1", _tocar(nivel_delta=-0.4))
    r = http.get("/api/v1/perfil/ana/progreso")
    assert r.status_code == 200
    d = r.json()
    assert d["user_id"] == "ana" and [u["unidad"] for u in d["unidades"]] == [1, 2, 3, 4]
    u2 = d["unidades"][1]
    assert u2["nivel_actual"] == 2.2 and u2["titulo"] == "Normativas de desarrollo y calidad del software"
    assert [p["nivel"] for p in u2["puntos"]] == [3.0, 2.6, 2.2]
    assert [p["motivo"] for p in u2["puntos"]] == ["inicial", "confusion", "confusion"]
    assert d["unidades"][0]["nivel_actual"] == 3.0 and len(d["unidades"][0]["puntos"]) == 1


def test_reiniciar_limpia_el_perfil(cliente):
    http, rag = cliente
    rag.perfiles.registrar_turno("ana", "c1", _tocar(nivel_delta=-0.4))
    r = http.post("/api/v1/perfil/ana/reiniciar")
    assert r.status_code == 200 and r.json()["es_nuevo"] is True and r.json()["nivel_por_unidad"]["2"] == 3.0
    assert not rag.perfiles.existe("ana")
    assert http.get("/api/v1/perfil/ana/progreso").json()["unidades"][1]["puntos"][-1]["nivel"] == 3.0


def test_reiniciar_es_solo_post(cliente):
    http, _ = cliente
    assert http.get("/api/v1/perfil/ana/reiniciar").status_code in (404, 405)


def test_user_id_vacio_o_demasiado_largo_se_rechaza(cliente):
    http, _ = cliente
    assert http.get("/api/v1/perfil/" + "a" * 101).status_code == 422


def test_perfil_responde_503_si_esta_desactivado(cliente):
    http, rag = cliente
    rag.perfiles = None
    for r in (http.get("/api/v1/perfil/ana"), http.get("/api/v1/perfil/ana/progreso"),
              http.post("/api/v1/perfil/ana/reiniciar")):
        assert r.status_code == 503
