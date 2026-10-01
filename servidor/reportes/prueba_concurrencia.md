# Prueba de concurrencia de la cola de generación

Generado el 2026-09-29 16:02 contra el RAG y el LLM reales (`MODELO_LLM=llama3.2`), en proceso (sin red, sin credenciales de Firebase: `usuario_actual` sustituido por un estudiante de prueba ya consentido). Cada nivel dispara N peticiones a `/api/v1/chat` EXACTAMENTE a la vez (`asyncio.gather`), cada una con su propia `conversation_id` y una pregunta real distinta (rotando un banco de 10), para no confundir la cola con aciertos de caché.

**Límite de generaciones simultáneas probado: `LIMITE_GENERACIONES_SIMULTANEAS = 2`** (espera máxima: 90 s).

## Resultados

| Peticiones | Errores | Duración total | Latencia servidor (media / p95) | Esperaron cupo | Posición máx. al llegar | Rendimiento |
|---|---|---|---|---|---|---|
| 10 | 0 | 30.15 s | 5.73 s / 8.17 s | 8 de 10 | 7 | 0.33 peticiones/s |
| 20 | 0 | 50.29 s | 5.01 s / 9.64 s | 14 de 20 | 13 | 0.4 peticiones/s |
| 40 | 0 | 78.48 s | 3.93 s / 10.71 s | 30 de 40 | 29 | 0.51 peticiones/s |

Positivo = petición resuelta con HTTP 200 (incluye respuestas, redirecciones, sin_contexto...: cualquier turno que el servidor completó). "Esperaron cupo" = la respuesta trajo `cola` (la petición encontró los cupos ocupados a su llegada). "Posición máx. al llegar" = el peor caso observado de cuántas peticiones ya esperaban cuando otra se puso en cola.

## 10 peticiones simultáneas

- Duración total del lote: **30.15 s** (0.33 peticiones/s de media).
- 10 de 10 resueltas con HTTP 200, sin errores.
- Latencia del servidor (`tiempo_respuesta_ms`): media 5732.9 ms, mediana 6574.2 ms, p95 8172.5 ms, máxima 8172.5 ms.
- 8 peticiones encontraron la cola ocupada a su llegada (de 10 resueltas); posición máxima observada al llegar: 7.
- De las que esperaron: espera media 15.16 s, máxima 23.74 s.

## 20 peticiones simultáneas

- Duración total del lote: **50.29 s** (0.4 peticiones/s de media).
- 20 de 20 resueltas con HTTP 200, sin errores.
- Latencia del servidor (`tiempo_respuesta_ms`): media 5008.4 ms, mediana 5644.5 ms, p95 9640.1 ms, máxima 9640.1 ms.
- 14 peticiones encontraron la cola ocupada a su llegada (de 20 resueltas); posición máxima observada al llegar: 13.
- De las que esperaron: espera media 22.00 s, máxima 43.77 s.

## 40 peticiones simultáneas

- Duración total del lote: **78.48 s** (0.51 peticiones/s de media).
- 40 de 40 resueltas con HTTP 200, sin errores.
- Latencia del servidor (`tiempo_respuesta_ms`): media 3929.8 ms, mediana 3693.4 ms, p95 10711.8 ms, máxima 14242.9 ms.
- 30 peticiones encontraron la cola ocupada a su llegada (de 40 resueltas); posición máxima observada al llegar: 29.
- De las que esperaron: espera media 38.67 s, máxima 72.64 s.

## Lectura

**Las tres corridas resolvieron el 100 % de las peticiones con HTTP 200, sin ningún error ni tiempo de espera
agotado**, con `LIMITE_GENERACIONES_SIMULTANEAS = 2` y `ESPERA_MAXIMA_COLA_S = 90`. El sistema se comporta como
se diseñó: en vez de intentar generar 10, 20 o 40 respuestas a la vez (que habría saturado la GPU y hecho más
lentas a todas, como ya se vio con modelos más grandes en `reportes/comparativa_modelos.md`), deja pasar 2 a la
vez y encola el resto — la latencia del servidor por petición se mantiene en el mismo rango en los tres niveles
(mediana 3.7-6.6 s) en vez de degradarse con la carga; lo que crece es cuánto tiene que esperar el final de la
cola, no cuánto tarda cada generación individual.

**El margen frente a `ESPERA_MAXIMA_COLA_S` se estrecha con la carga**: con 40 peticiones, la espera máxima
observada (72,64 s) ya está a menos de 20 s del tope de 90 s. Con más de 40 estudiantes preguntando exactamente
a la vez (poco probable en una sesión real, donde las preguntas se escalonan; aquí se dispararon con
`asyncio.gather`, es decir, deliberadamente peor que cualquier caso real), algunas empezarían a recibir el 503
de tiempo agotado. Si en una sesión real se ve esto, las dos palancas son `LIMITE_GENERACIONES_SIMULTANEAS`
(si el hardware tiene margen: esta prueba no lo determina, solo midió con 2) y `ESPERA_MAXIMA_COLA_S`.

**Latencia de cliente vs. de servidor**: la de cliente (hasta 78 s en el peor caso de 40) incluye el tiempo en
cola; la de servidor (`tiempo_respuesta_ms`, lo que se guarda y se le muestra al estudiante) es solo la
generación en sí. La app debe mostrar la espera con el campo `cola` de la respuesta (posición y estimación) en
vez de dejar al estudiante viendo una petición HTTP colgada sin explicación — es justo para eso que existe.

**Un bug real, encontrado y corregido en el guion de prueba (no en el servidor)**: la primera corrida de este
guion llamaba `asyncio.run()` una vez por nivel (10, luego 20, luego 40), y `services/cola_service.py` guarda
su `asyncio.Semaphore`/`asyncio.Lock` como un singleton de módulo — atado al primer event loop en el que se
usa. Un segundo `asyncio.run()` (un event loop nuevo) rompía esos objetos con `RuntimeError: ... is bound to a
different event loop`, y los niveles de 20 y 40 fallaban en más de la mitad de las peticiones. La causa es
exclusiva de este guion (llama a la cola dentro de varios event loops sucesivos, algo que un proceso de
uvicorn real nunca hace: corre un único event loop durante toda su vida) — se corrigió envolviendo los tres
niveles en un solo `asyncio.run()` (ver `_todos_los_niveles` en `scripts/prueba_concurrencia.py`); los números
de esta tabla son de la corrida ya corregida.

