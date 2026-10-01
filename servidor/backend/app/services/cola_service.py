"""Cola de peticiones al modelo: con un solo LLM local (Ollama) en una GPU/CPU concretas, generar dos respuestas
a la vez no las hace más rápidas — las hace más lentas a las dos (satura la VRAM/CPU: ver
reportes/comparativa_modelos.md, donde ya se vio esa clase de degradación con modelos más grandes). En vez de
dejar que 40 estudiantes disparen 40 generaciones simultáneas, se limita a `LIMITE_GENERACIONES_SIMULTANEAS` y el
resto espera su turno — reportando su posición y una estimación de espera para que el cliente la muestre, con un
tope de espera (`ESPERA_MAXIMA_COLA_S`) para no dejar una petición colgada sin respuesta.

Cuatro decisiones de diseño, deliberadas:

1. **`asyncio.Semaphore`, no `threading.Semaphore`.** El threadpool que Starlette usa para correr código
   síncrono (`starlette.concurrency.run_in_threadpool`, que llama a `anyio.to_thread.run_sync`) tiene un límite
   bajo por defecto (40 hilos: `anyio.to_thread.current_default_thread_limiter().total_tokens`). Si 40
   estudiantes quedaran BLOQUEADOS ESPERANDO turno dentro de ese pool, ocuparían los 40 hilos y el servidor
   dejaría de poder atender NINGUNA petición más, ni siquiera una que no toque el modelo (como GET
   /cola/estado). Por eso la espera (`turno()`) es una corrutina que se espera con `await` en el event loop —no
   consume ningún hilo del pool mientras espera— y SOLO la generación en sí, ya con el cupo conseguido, se
   despacha a un hilo (porque llamar a Ollama es una operación bloqueante). El número de hilos ocupados por la
   cola en un momento dado queda acotado por `LIMITE_GENERACIONES_SIMULTANEAS` (los que están generando de
   verdad), nunca por cuántos están esperando.

2. **Los aciertos de caché nunca pasan por aquí.** Responden en ~20 ms sin llamar al modelo
   (`RAGService.probar_cache`, `cache_service.py`); encolarlos detrás de una generación de varios segundos
   convertiría la ventaja del caché en una espera. `api/v1/endpoints/chat.py` prueba el caché primero, y solo si
   falla entra a `turno()`.

3. **Las llamadas cortas del propio turno (clasificar pertinencia, reformular un seguimiento, redirigir) SÍ
   pasan por la cola, junto con la generación de la respuesta.** No se encolan aparte: van todas dentro de la
   misma llamada a `RAGService.get_answer()` que ya está usando el cupo. Se decidió así porque las tres compiten
   por el mismo Ollama y la misma GPU/CPU que la generación — dejarlas correr sin control fuera de la cola no
   evitaría la saturación que la cola existe para prevenir, solo la movería de la generación a la clasificación
   (que además es previa y obligatoria: no hay forma de generar sin haber clasificado antes).

4. **Espera máxima y estimación con datos reales.** `turno()` usa `asyncio.wait_for` con
   `ESPERA_MAXIMA_COLA_S`: pasado ese tiempo, `TiempoDeEsperaAgotado` (que el endpoint traduce a un 503 con un
   mensaje claro) en vez de dejar la conexión HTTP colgada. La estimación de espera de quien llega se calcula
   con la media móvil de lo que tardaron las últimas generaciones REALES (`_tiempos`, ventana de 20), no con una
   constante: se ajusta sola si el modelo, el prompt o la máquina cambian.
"""
import asyncio
import time
from collections import deque
from contextlib import asynccontextmanager
from dataclasses import dataclass


@dataclass(frozen=True)
class EstadoCola:
    """Foto en vivo de la cola, para GET /api/v1/cola/estado."""
    limite: int
    generando: int
    en_espera: int
    tiempo_medio_generacion_s: float
    espera_maxima_s: float

    def como_dict(self) -> dict:
        return {"limite": self.limite, "generando": self.generando, "en_espera": self.en_espera,
                "tiempo_medio_generacion_s": self.tiempo_medio_generacion_s, "espera_maxima_s": self.espera_maxima_s}


@dataclass(frozen=True)
class Espera:
    """Lo que le costó a UNA petición concreta entrar a generar: se adjunta a la respuesta del chat cuando la
    cola estaba ocupada a su llegada, para que el cliente sepa por qué tardó."""
    ocupada: bool             # ¿tuvo que esperar? (había alguien delante, o tardó más que un margen mínimo)
    posicion_al_llegar: int   # cuántas peticiones tenía delante al llegar (0 = pasó directo)
    espera_estimada_s: float  # estimación hecha AL LLEGAR (posición × media móvil de generaciones reales)
    espera_real_s: float      # lo que realmente tardó en conseguir un cupo

    def como_dict(self) -> dict:
        return {"ocupada": self.ocupada, "posicion_al_llegar": self.posicion_al_llegar,
                "espera_estimada_s": self.espera_estimada_s, "espera_real_s": self.espera_real_s}


class TiempoDeEsperaAgotado(Exception):
    """La petición esperó más de `espera_maxima_s` sin conseguir un cupo de generación."""

    def __init__(self, posicion_al_llegar: int, espera_maxima_s: float):
        self.posicion_al_llegar = posicion_al_llegar
        self.espera_maxima_s = espera_maxima_s
        super().__init__(
            f"El tutor está saturado: más de {espera_maxima_s:.0f} s esperando turno "
            f"(posición al llegar: {posicion_al_llegar}). Intenta de nuevo en un momento.")


class ColaGeneracion:
    def __init__(self, limite: int, espera_maxima_s: float, ventana_tiempos: int = 20, tiempo_inicial_s: float = 5.0):
        self.limite = max(1, limite)
        self.espera_maxima_s = espera_maxima_s
        self._semaforo = asyncio.Semaphore(self.limite)
        self._lock = asyncio.Lock()
        self._generando = 0
        self._en_espera = 0
        self._tiempos: deque[float] = deque([tiempo_inicial_s], maxlen=ventana_tiempos)

    async def estado(self) -> EstadoCola:
        async with self._lock:
            return EstadoCola(self.limite, self._generando, self._en_espera, self._media_tiempos(),
                              self.espera_maxima_s)

    def _media_tiempos(self) -> float:
        return round(sum(self._tiempos) / len(self._tiempos), 2)

    @asynccontextmanager
    async def turno(self):
        """Espera (en el event loop, sin ocupar un hilo) hasta conseguir un cupo, o lanza
        `TiempoDeEsperaAgotado` pasados `espera_maxima_s`. Uso:
            async with cola.turno() as espera:
                resultado = await run_in_threadpool(rag_service.get_answer, ...)
            # espera.posicion_al_llegar / espera_real_s ya están listos para adjuntar a la respuesta
        """
        async with self._lock:
            posicion = self._en_espera
            estimada = round(posicion * self._media_tiempos(), 2)
            self._en_espera += 1
        inicio_espera = time.perf_counter()
        try:
            await asyncio.wait_for(self._semaforo.acquire(), timeout=self.espera_maxima_s)
        except asyncio.TimeoutError:
            async with self._lock:
                self._en_espera -= 1
            raise TiempoDeEsperaAgotado(posicion, self.espera_maxima_s) from None
        espera_real = round(time.perf_counter() - inicio_espera, 2)
        async with self._lock:
            self._en_espera -= 1
            self._generando += 1
        info = Espera(ocupada=posicion > 0 or espera_real > 0.05, posicion_al_llegar=posicion,
                      espera_estimada_s=estimada, espera_real_s=espera_real)
        inicio_generacion = time.perf_counter()
        try:
            yield info
        finally:
            duracion = time.perf_counter() - inicio_generacion
            async with self._lock:
                self._generando -= 1
                self._tiempos.append(duracion)
            self._semaforo.release()
