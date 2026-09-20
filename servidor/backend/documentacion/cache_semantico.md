# Caché semántico de respuestas

Evita volver a llamar a Ollama cuando llega una pregunta que ya se respondió. Código: `app/services/cache_service.py`
(almacén SQLite y búsqueda), integración en `RAGService.get_answer` (`app/services/rag_service.py`) y estadísticas en
`GET /api/v1/cache/estadisticas` (`app/api/v1/endpoints/cache.py`).

## Funcionamiento

1. Llega una pregunta → se calcula su embedding con `sentence-transformers/all-MiniLM-L6-v2` (el mismo del RAG).
2. Se busca en `servidor/cache_respuestas.db` (SQLite; no hay copia en memoria, sobrevive a reinicios) la entrada más
   parecida por similitud coseno. Si llega a `CACHE_UMBRAL_SIMILITUD` se devuelve su respuesta **sin recuperar
   fragmentos ni llamar a ningún LLM**, se incrementa su contador de usos y se actualiza su fecha de último uso.
3. Si no, se genera la respuesta como siempre y, si es una respuesta basada en los documentos (`tipo` `respuesta` o
   `sin_contexto`), se guarda: pregunta original, embedding, respuesta, contexto y documentos fuente recuperados,
   contador de usos (0 al crearse; cuenta reutilizaciones), fecha de creación, fecha de último uso y lo que tardó en
   generarse.
4. `POST /api/v1/chat` devuelve además `desde_cache` (bool) y `tiempo_respuesta_ms` (float, tiempo en el servidor).

Configuración (`core/config.py`, variables de entorno): `CACHE_ACTIVO` (true), `CACHE_UMBRAL_SIMILITUD` (0.95),
`CACHE_DB_PATH` (`servidor/cache_respuestas.db`). El archivo `.db` está en `servidor/.gitignore`.

### Qué no pasa por el caché

- Saludos (mensaje fijo), preguntas sobre el propio tutor (dependen de los documentos cargados en ese momento).
- **Seguimientos dentro de una conversación** ("explícame eso mejor", mensajes de ≤3 palabras...): su respuesta
  depende del historial, no solo de la pregunta. Ni se consultan ni se guardan.
- No se guardan `redireccion` (su redacción varía a propósito), `sin_documentos` ni `error`.
- Un acierto sí se añade a la memoria de la conversación, para que un seguimiento posterior pueda apoyarse en él.

## Invalidación

Cualquier cambio del índice vacía **todo** el caché: subir un documento nuevo o modificado (`POST /documentos/subir`),
`POST /documentos/reindexar`, y también al arrancar si `sincronizar()` encuentra documentos nuevos, cambiados o
borrados mientras el servidor estaba apagado. Los ganchos están en el servicio (`indexar_archivo`, `reconstruir`,
`sincronizar`), así que cualquier camino que modifique el índice los ejecuta. No se invalida si el índice no cambia
(archivo repetido → `omitido_sin_cambios`; archivo rechazado).

Dos protecciones para que nunca se sirva una respuesta posiblemente desactualizada:

- **Versión**: el caché guarda un contador que sube en cada invalidación. Una respuesta se guarda solo si la versión
  no cambió desde que empezó a generarse; una respuesta calculada con el índice anterior mientras se subía un
  documento se descarta (el LLM tarda segundos; la carga corre en otro hilo).
- **Invalidación fallida**: si vaciar el SQLite falla, queda pendiente y el caché no se usa hasta lograr vaciarlo.

Los contadores de aciertos/fallos y el tiempo ahorrado se conservan al invalidar (son la evidencia acumulada); las
entradas y, por tanto, "preguntas más repetidas", no.

## Por qué 0.95 y no 0.92 (calibración)

`python scripts/calibrar_cache.py` mide pares de preguntas con los embeddings reales (sin LLM). Con
all-MiniLM-L6-v2 sobre texto en español, la similitud **no separa** bien "la misma pregunta redactada distinto" de
"otra pregunta parecida":

| Tipo de par | Similitud |
|---|---|
| Misma pregunta, cambios de forma ("Oye, ¿qué es…", "…, por favor", minúsculas, "exactamente") | 0.960 – 0.990 |
| Misma pregunta, cambio de "la norma ISO 25010" a "la ISO 25010" o "ISO/IEC 25010" | 0.808 – 0.867 |
| Misma pregunta, reformulada de fondo ("Dime en qué consiste…", "Explícame la ISO…") | 0.609 – 0.897 |
| Otra norma, misma frase ("ISO 9001" / "ISO 27001", "25010" / "12207") | 0.902 – 0.919 |
| Pregunta opuesta ("qué es" / "qué **no** es") | 0.974 |
| Otra pregunta sobre el mismo tema ("qué es" / "cuáles son las **características** de") | **0.927** |

Consecuencias:

- **Solo por similitud sería incorrecto**: 0.92 devolvería la respuesta de "qué es" a "características", y ninguna
  similitud evita que "qué es ISO 25010" y "qué **no** es ISO 25010" (0.974) se confundan. Por eso un acierto exige,
  además del umbral, que ambas preguntas coincidan en (filtros previos en SQL, sin LLM): el modo de respuesta
  (`TAREA`/`PROFUNDIZAR`/`PUNTUAL` por señales explícitas), los **números y siglas** que nombran (ISO 9001 ≠ 27001,
  CMMI ≠ SPICE) y la **negación**. Con eso, el único par distinto que queda por encima de 0.92 es el de
  "características".
- **0.95** deja fuera ese par y conserva todos los aciertos legítimos de la muestra (4 de 4 con cambios de forma).
  Es un margen fino (0.927 vs 0.960) sobre una muestra pequeña (19 pares): si se amplía el corpus de preguntas,
  recalibrar.
- Las **reformulaciones de fondo no acertarán**: se generan de nuevo. Es el coste de no dar respuestas de otra
  pregunta; para acertarlas con seguridad haría falta un modelo de embeddings multilingüe o un reranker.
  Bajar el umbral (p. ej. `CACHE_UMBRAL_SIMILITUD=0.85`) sube los aciertos y también las respuestas equivocadas.

Limitaciones conocidas: siglas escritas en minúsculas ("que es cmmi" / "que es spice") no las detecta la huella;
preguntas distintas con estructura casi idéntica y sin números/siglas/negación de por medio pueden superar el umbral;
no hay política de expulsión (el caché solo crece hasta la próxima invalidación); si se cambia el modelo de
embeddings hay que vaciar el caché a mano (las entradas de otra dimensión se ignoran, pero de igual dimensión no).

## Resultados medidos (servidor real, Ollama `llama3.2`, embeddings reales, 2026-09-20)

Misma pregunta, tres redacciones, umbral 0.95:

| # | Pregunta | Similitud con la 1ª | `desde_cache` | `tiempo_respuesta_ms` |
|---|---|---|---|---|
| 1 | ¿Qué es la norma ISO 25010? | — | false | 5 521,5 |
| 2 | Oye, ¿qué es la norma ISO 25010? | 0,990 | **true** | **7,4** |
| 3 | ¿Qué es exactamente la norma ISO 25010? | 0,967 | **true** | **7,4** |

Respuestas 1 = 2 = 3 (idénticas). Una reformulación de fondo ("¿Podrías explicarme qué es ISO 25010?", 0,786) y una
pregunta distinta del mismo tema ("¿Cuáles son las características de la norma ISO 25010?") **no** acertaron y se
generaron (7 602 ms y 2 917 ms). Tras 5 consultas: tasa de aciertos 0,40 (2/5), tiempo promedio ahorrado 5 514 ms
por acierto.

Persistencia: tras detener y volver a arrancar el servidor, la misma pregunta acertó con las 3 entradas y los
contadores intactos (25,8 ms en la primera consulta tras el arranque).

Invalidación (endpoints reales): subir `prueba_cache.md` → 3 entradas → 0 (motivo "documento indexado:
prueba_cache.md") y la siguiente pregunta se regeneró (1 827 ms); reenviar el mismo archivo (`omitido_sin_cambios`) no
vació el caché; `POST /documentos/reindexar` lo vació (motivo "reindexado completo").

La prueba se hizo sobre copias de `documentacion/` y `base_vectorial/` para no modificar las versionadas.
Nota para la tesis: el tiempo ahorrado es una **estimación** (lo que costó generar la respuesta la primera vez menos
lo que tardó en servirse desde el caché); la latencia del LLM depende de la máquina (7-45 s en la batería del tutor).

## Tests

`tests/test_cache.py` (36 tests): umbral y su configurabilidad, persistencia, salvaguardas con los pares medidos
arriba, versión/invalidación, estadísticas (tasa, top 10, tiempo ahorrado, sin división por cero), y con `RAGService`
+ endpoints reales: un acierto no llama a ningún LLM, seguimientos y tipos no cacheables, invalidación al subir /
modificar / reindexar / reiniciar con documentos cambiados, carrera de generación durante una carga, y que un fallo del
caché nunca impida responder. Se comprobó que cada gancho de invalidación, al eliminarlo, hace fallar algún test.
