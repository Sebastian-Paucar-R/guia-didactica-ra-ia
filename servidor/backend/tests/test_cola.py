"""Cola de generación (app/services/cola_service.py): límite de generaciones simultáneas, posición y estimación
de espera, tope de espera máxima. Pruebas con asyncio real (pytest-asyncio, asyncio_mode=auto en pytest.ini):
`turno()` bloquea de verdad, así que se coordinan corrutinas concurrentes con asyncio.gather / asyncio.sleep, no
con mocks del reloj."""
import asyncio

import pytest

from app.services.cola_service import ColaGeneracion, TiempoDeEsperaAgotado


async def test_una_sola_peticion_pasa_directo_sin_esperar():
    cola = ColaGeneracion(limite=2, espera_maxima_s=5)
    async with cola.turno() as espera:
        await asyncio.sleep(0.01)
    assert espera.ocupada is False and espera.posicion_al_llegar == 0


async def test_dentro_del_limite_nadie_espera():
    cola = ColaGeneracion(limite=2, espera_maxima_s=5)
    esperas = []

    async def turno():
        async with cola.turno() as espera:
            esperas.append(espera)
            await asyncio.sleep(0.05)

    await asyncio.gather(turno(), turno())
    assert all(not e.ocupada for e in esperas)


async def test_la_tercera_peticion_espera_si_el_limite_es_dos():
    """asyncio.gather no garantiza que las tres corrutinas entren a turno() en orden estricto (hay un await -el
    lock interno- antes de tomar el semáforo): se escalonan las tres a propósito para que el orden sea
    determinista, en vez de confiar en el orden de creación de las tareas."""
    cola = ColaGeneracion(limite=2, espera_maxima_s=5, tiempo_inicial_s=0.2)
    orden_entrada = []
    resultados = {}

    async def turno(nombre, duracion):
        async with cola.turno() as espera:
            orden_entrada.append(nombre)
            await asyncio.sleep(duracion)
        resultados[nombre] = espera

    tareas = []
    for nombre in ("a", "b", "c"):
        tareas.append(asyncio.create_task(turno(nombre, 0.3)))
        await asyncio.sleep(0.05)   # deja que cada una entre a turno() antes de lanzar la siguiente
    await asyncio.gather(*tareas)

    assert resultados["a"].posicion_al_llegar == 0 and resultados["b"].posicion_al_llegar == 0   # 2 cupos libres
    assert resultados["c"].posicion_al_llegar == 0   # nadie más esperaba TODAVÍA cuando c se puso en cola
    assert resultados["c"].ocupada and resultados["c"].espera_real_s > 0.1   # pero sí tuvo que esperar de verdad
    assert orden_entrada[:2] == ["a", "b"]


async def test_la_posicion_cuenta_cuantos_hay_esperando_delante_al_llegar():
    """`posicion_al_llegar` cuenta cuántas peticiones están YA EN COLA DE ESPERA al llegar, no cuántas existen en
    total: quien está generando (tiene el cupo) no cuenta como "delante en la cola", solo como el motivo de la
    espera. Con límite 1: la 1ª entra directo (posición 0); la 2ª es la primera en esperar (también ve la cola
    en 0, porque nadie más estaba esperando todavía, solo generando); la 3ª sí ve a la 2ª esperando (posición 1)."""
    cola = ColaGeneracion(limite=1, espera_maxima_s=5, tiempo_inicial_s=0.05)
    posiciones = []

    async def turno():
        async with cola.turno() as espera:
            posiciones.append(espera.posicion_al_llegar)
            await asyncio.sleep(0.2)

    tareas = []
    for _ in range(3):
        tareas.append(asyncio.create_task(turno()))
        await asyncio.sleep(0.03)
    await asyncio.gather(*tareas)
    assert posiciones == [0, 0, 1]


async def test_se_agota_la_espera_maxima():
    cola = ColaGeneracion(limite=1, espera_maxima_s=0.05, tiempo_inicial_s=1)

    async def ocupar():
        async with cola.turno():
            await asyncio.sleep(0.3)

    async def esperar_de_mas():
        async with cola.turno():
            pass

    tarea_ocupada = asyncio.create_task(ocupar())
    await asyncio.sleep(0.02)   # deja que "ocupar" tome el único cupo
    with pytest.raises(TiempoDeEsperaAgotado) as exc:
        await esperar_de_mas()
    assert exc.value.posicion_al_llegar == 0 and exc.value.espera_maxima_s == 0.05
    assert "saturado" in str(exc.value) and "posición al llegar: 0" in str(exc.value)
    await tarea_ocupada


async def test_el_cupo_se_libera_aunque_la_generacion_falle():
    cola = ColaGeneracion(limite=1, espera_maxima_s=5)

    with pytest.raises(RuntimeError):
        async with cola.turno():
            raise RuntimeError("Ollama caído")

    # si el cupo no se liberó, esto se quedaría esperando hasta agotar espera_maxima_s
    async with cola.turno() as espera:
        assert not espera.ocupada


async def test_la_estimacion_usa_la_media_movil_de_generaciones_reales():
    cola = ColaGeneracion(limite=1, espera_maxima_s=5, tiempo_inicial_s=999, ventana_tiempos=3)

    async def turno(duracion):
        async with cola.turno():
            await asyncio.sleep(duracion)

    await turno(0.05)   # la media ya no es la inicial (999) sino ~0.05

    esperando = asyncio.Event()

    async def ocupar():
        async with cola.turno():
            esperando.set()
            await asyncio.sleep(0.05)

    tarea = asyncio.create_task(ocupar())
    await esperando.wait()
    async with cola.turno() as espera:
        pass
    assert espera.espera_estimada_s < 5   # nada parecido a la constante inicial (999) ni desproporcionado
    await tarea


async def test_estado_refleja_limite_generando_y_en_espera():
    cola = ColaGeneracion(limite=1, espera_maxima_s=5, tiempo_inicial_s=0.2)
    estado_inicial = await cola.estado()
    assert (estado_inicial.limite, estado_inicial.generando, estado_inicial.en_espera) == (1, 0, 0)

    en_generacion = asyncio.Event()

    async def ocupar():
        async with cola.turno():
            en_generacion.set()
            await asyncio.sleep(0.1)

    tarea = asyncio.create_task(ocupar())
    await en_generacion.wait()
    estado_ocupado = await cola.estado()
    assert estado_ocupado.generando == 1
    await tarea


def test_como_dict_de_espera_y_estado():
    from app.services.cola_service import Espera, EstadoCola
    e = Espera(ocupada=True, posicion_al_llegar=2, espera_estimada_s=1.5, espera_real_s=1.8)
    assert e.como_dict() == {"ocupada": True, "posicion_al_llegar": 2, "espera_estimada_s": 1.5, "espera_real_s": 1.8}
    s = EstadoCola(limite=2, generando=1, en_espera=0, tiempo_medio_generacion_s=3.2, espera_maxima_s=90.0)
    assert s.como_dict() == {"limite": 2, "generando": 1, "en_espera": 0, "tiempo_medio_generacion_s": 3.2,
                             "espera_maxima_s": 90.0}
