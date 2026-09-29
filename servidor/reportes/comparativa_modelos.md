# Comparativa de modelos de Ollama para el tutor

Generado a mano el 2026-09-29 a partir de corridas reales contra el servidor (no simulado). Compara `llama3.2`
(el modelo actual) contra tres candidatos mayores — `llama3.1:8b`, `qwen2.5:7b-instruct`, `mistral:7b` — con todo
lo demás sin cambiar: mismo índice (copia de `base_vectorial/`), mismo umbral de pertinencia, mismo prompt,
caché y perfiles nuevos por modelo. Hardware: portátil con GPU NVIDIA RTX 3060 (6 GB VRAM), 16 GB RAM.

## Metodología

- **Filtro y latencia**: `pruebas/banco_comparativa_modelos.json` (muestra estratificada de `banco_consultas.json`:
  3 preguntas por unidad + 6 fuera de temario = 18), una pasada, contra `pruebas/evaluar_tutor.py`.
- **Atribuciones falsas**: la parte 1 de `pruebas/casos_adaptacion.json` (3 preguntas × 3 perfiles = 9 respuestas
  por modelo: ISO 9001, ISO/IEC 25010, ISO/IEC/IEEE 12207, cada una para un estudiante novato, uno sin perfil y
  uno avanzado), sin la parte de evolución (`--sin-evolucion`, para acotar el tiempo). **Contadas por lectura**,
  como pide el encargo: no por el veredicto automático (ver "Límites de esta comparativa").
- Cada modelo corrió en su propio servidor real (`uvicorn`), uno a la vez (la GPU no tiene VRAM para dos modelos
  de 4-5 GB a la vez), con `CACHE_DB_PATH`/`PERFIL_DB_PATH` nuevos para no arrastrar nada de una corrida a otra.
- **Nota sobre el entorno**: durante la primera corrida de `mistral:7b` el sistema se quedó sin memoria (RAM
  libre por debajo de 2,5 GB de 16 GB) y el proceso se detuvo antes de generar ninguna respuesta; la causa
  fue otra aplicación (~4 GB) corriendo en la misma máquina, no esta comparativa. Se repitió sola, con memoria
  libre, y esos son los resultados de abajo.

## Resultados

| Modelo | Precisión del filtro (18 preguntas) | Latencia media, banco de filtro | Latencia media, banco de adaptación | Atribuciones falsas leídas (de 9) |
|---|---|---|---|---|
| **llama3.2** (actual) | 100 % (18/18) | **2,4 s** (mediana 1,9 s; p95 6,6 s) | **3,6 s** (1,7–8,1 s) | **0** |
| llama3.1:8b | 100 % (18/18) | 11,0 s (mediana 10,1 s; p95 20,3 s) | 22,6 s (12,5–40,2 s) | **1** |
| qwen2.5:7b-instruct | 100 % (18/18) | 16,6 s (mediana 14,2 s; p95 36,5 s) | 24,6 s (12,5–46,1 s) | 0 |
| mistral:7b | 100 % (18/18) | 10,3 s (mediana 8,8 s; p95 22,5 s) | 30,3 s (4,5–**138,3 s**) | 0 |

Los cuatro acertaron el filtro de pertinencia al 100 % en esta muestra (18 preguntas: 12 dentro del temario, una
por unidad × 3, y 6 fuera). No es sorpresa: el filtro usa palabras clave y embeddings antes que el LLM en la
mayoría de los casos (ver `pertinencia_service.py`), así que el modelo de generación influye poco ahí; es la
base de la opción híbrida (ver más abajo).

**Los tres candidatos son entre 4× y 7× más lentos que `llama3.2`** en generación, y muy por encima en la cola:
`llama3.1:8b` y `qwen2.5` llegan a 40-46 s en una sola respuesta, y `mistral:7b` tuvo un caso de **138 segundos**
(una respuesta a "¿Qué es ISO/IEC 25010?" que además salió casi vacía). Con 4-5 GB de pesos cuantizados en una
GPU de 6 GB y `NUM_CTX=8192`, es probable que no quepan enteros en VRAM y haya volcado parte a CPU; en una GPU
con más memoria estos tiempos bajarían, pero **con el hardware real de este proyecto la diferencia es enorme**.

## Lectura de las respuestas (atribuciones falsas)

Con solo 9 respuestas por modelo esto es indicativo, no una medida estadística — ver "Límites" abajo. Detalle
completo (las 4×9 respuestas) en `reportes/` no se versiona (son corridas locales); resumen de lo encontrado:

- **llama3.2**: ninguna atribución cruzada clara. Las 6 respuestas sobre ISO 9001 e ISO/IEC/IEEE 12207 son
  correctas y están bien ancladas al contexto (incluye detalles reales como el año 1987 de ISO 9001 o la
  sección 14 "Glosario breve" de la 12207, verificados contra los `.md`). Las 3 respuestas sobre ISO/IEC 25010
  no explican la norma con claridad (ver el problema de recuperación abajo), pero tampoco inventan datos
  atribuidos a ella. Un defecto aparte: la respuesta "avanzado" de A2 dejó escapar literalmente la palabra
  "CONTEXTO" (el nombre de la variable del prompt) en el texto — una fuga de prompt, no de contenido.
- **llama3.1:8b**: **una atribución cruzada real.** En A1 ("estándar"), la pregunta de cierre dice: *"¿Cómo
  crees que se relacionaría el 'pensamiento basado en riesgos' introducido por ISO 31000 con los principios...
  de ISO 9001?"* — pero el propio documento indexado dice lo contrario: *"La versión de 2015 [de ISO 9001]...
  introdujo el pensamiento basado en riesgos"* y que ISO 31000 lo *"refuerza"*, no lo introduce
  (`ISO_9001_Gestion_Calidad.md`, líneas 19 y 112). Es exactamente el fallo que este encargo busca corregir. **La
  verificación automática de atribución por oración (punto 3) NO lo atrapa**: la oración nombra dos normas (9001
  y 31000) a la vez, y el chequeo, a propósito, solo exige que cada norma nombrada tenga algún fragmento propio
  recuperado (lo tenían las dos) para no generar falsos positivos en contrastes legítimos — ver "Límites".
- **qwen2.5:7b-instruct**: ninguna atribución cruzada clara encontrada. Tiende a ser más lacónico cuando el
  contexto es débil (A2) en vez de rellenar con otras normas, lo cual es el comportamiento correcto.
- **mistral:7b**: ninguna atribución cruzada clara, pero dos defectos de forma: la respuesta a A2/novato
  encadena dos preguntas de reflexión en vez de una (viola la regla del prompt), y la respuesta a A2/estándar
  (la de 138 s) salió casi vacía ("¿Qué otra norma del software te resultaría interesante investigar?", sin
  explicar nada). Menos fiable en tiempo de respuesta que en contenido.

### Un problema transversal, no de ningún modelo: la recuperación para "¿Qué es ISO/IEC 25010?"

En los cuatro modelos, las 3 respuestas sobre ISO/IEC 25010 fueron pobres o evasivas. La causa no es el LLM: la
**recuperación** (embeddings `all-MiniLM-L6-v2`, sin cambios en esta comparativa) no trae el propio documento de
ISO/IEC 25010 entre los 4 fragmentos para esa pregunta exacta — se comprobó con `buscar_con_score` (fuera de
esta comparativa) y los 4 fragmentos más parecidos fueron de ISO/IEC 29110, ISO 9001 (×2) e ISO/IEC 27002, con
scores 0,71-0,72, a pesar de que el documento de ISO/IEC 25010 empieza con una definición directa de la norma.
Como "25010" aparece mencionado de pasada dentro del fragmento de ISO 9001 ("complementando normas específicas
como ISO/IEC 25010"), `terminos_sin_respaldo` no lo marca como sin respaldo (el número sí aparece en la base),
así que el tutor no cae automáticamente en `sin_contexto`; queda a criterio del modelo, y ninguno de los cuatro
resolvió bien esa situación. Esto es un problema de **calidad de recuperación**, no de generación, y queda fuera
del alcance de este encargo (ya estaba anotado como pendiente en `BITACORA.md`: "un modelo de embeddings
multilingüe permitiría acertar reformulaciones... con seguridad"); se documenta aquí porque explica por qué las
respuestas sobre 25010 son las más débiles de la muestra en los cuatro modelos por igual.

## Límites de esta comparativa

- **Muestra pequeña**: 9 respuestas por modelo para atribuciones y 18 preguntas para el filtro. Un solo caso de
  atribución cruzada (llama3.1:8b) o de latencia extrema (mistral:7b) puede no ser representativo; no se puede
  concluir con esto que llama3.2 nunca falla o que los otros tres fallan sistemáticamente más.
- **Blind spot conocido de la verificación automática** (punto 3 de este encargo): con dos o más normas en la
  misma oración, `atribuciones_no_respaldadas` solo exige que cada norma nombrada tenga algún fragmento propio
  recuperado, no verifica a cuál de las dos pertenece cada afirmación (para no penalizar contrastes legítimos,
  que el perfil "comparativo" pide a propósito). El caso real de llama3.1:8b (arriba) es exactamente ese punto
  ciego: dos normas en una sola oración, cada una con su propio fragmento recuperado, pero el hecho concreto
  mal atribuido entre ellas. Tasa de falsos positivos observada del chequeo con una sola norma por oración: 0
  en las ~36 respuestas leídas de esta comparativa (no marcó ningún caso correcto como inválido); tasa de falsos
  negativos (como este) no medible con una muestra tan chica, pero se sabe que es mayor que cero.
- **No se corrió la variante híbrida** (clasificador `llama3.2` + generador mayor) de forma real en esta sesión,
  por el tiempo y el incidente de memoria descrito arriba. El mecanismo ya está implementado y lo respalda el
  propio dato de esta tabla: el filtro decide casi siempre por palabras clave o similitud de embeddings, no por
  el LLM clasificador (ver "Resultados"), así que cambiar solo el modelo de generación no debería tocar la
  precisión del filtro; el análisis razonado está en "Recomendación".

## Recomendación

**Mantener `llama3.2` como modelo por defecto** (`MODELO_LLM`), sin activar `MODELO_CLASIFICADOR` con un modelo
distinto, por ahora. Razones, con los datos de arriba:

1. **Ningún candidato mostró mejor calidad de atribución que la base** en esta muestra: `llama3.2` fue el único
   con cero atribuciones cruzadas encontradas por lectura y sin el defecto de forma de `mistral:7b`; `llama3.1:8b`
   (el "mayor" más citado como opción) cometió el único error de atribución cruzada real de los cuatro.
2. **La latencia es entre 4× y 7× peor** con los tres candidatos, y con colas de hasta 40-138 s por respuesta:
   en un tutor conversacional real esa espera es un problema de producto tan serio como una atribución mal
   hecha. Con el hardware de este proyecto (GPU de 6 GB), un modelo de 7-8B no entra completo en VRAM.
3. La corrección de fondo pedida en este encargo (puntos 2-5: acotar la extensión al contexto recuperado,
   verificar atribución por oración, corregir los dos defectos del filtro, endurecer los veredictos) **son
   correcciones de código, no del modelo**: se aplican igual sin importar qué LLM genere la respuesta, y ya
   están implementadas y probadas (ver `BITACORA.md`).
4. **La opción híbrida queda disponible pero no se recomienda activarla todavía**: no se pudo medir su ventaja
   real de calidad en generación (no se corrió con datos reales) y, aunque el clasificador ya es barato, la
   mayor parte del tiempo que un estudiante espera es la respuesta final, que seguiría siendo 4-7× más lenta.

**Cuándo reconsiderar**: si se despliega en un servidor con más VRAM (o un modelo alojado por API en vez de
local), vale la pena repetir esta comparativa con un banco más grande (`banco_consultas.json` completo, 60
preguntas, y las 9 respuestas de `casos_adaptacion.json` con la parte de evolución incluida) antes de cambiar el
valor por defecto — el mecanismo (`MODELO_LLM` / `MODELO_CLASIFICADOR` en `.env`) ya está listo para ese cambio
sin tocar código.

## Cómo se corrió

Copia de `base_vectorial/`, `cache_respuestas.db` y `perfiles.db` nuevos por configuración, variables de entorno
antes de arrancar (`MODELO_LLM`, `BASE_VECTORIAL_DIR`, `CACHE_DB_PATH`, `PERFIL_DB_PATH`, `PYTHONUTF8=1`):

```
python -m uvicorn app.main:app --app-dir backend --port 8010
python pruebas/evaluar_tutor.py --url http://127.0.0.1:8010 --banco pruebas/banco_comparativa_modelos.json \
    --pasadas 1 --etiqueta "<modelo>" --salida-json reportes/tmp_filtro.json --salida-md reportes/tmp_filtro.md
python pruebas/evaluar_adaptacion.py --url http://127.0.0.1:8010 --sin-evolucion --etiqueta "<modelo>" \
    --salida-json reportes/tmp_adapt.json --salida-md reportes/tmp_adapt.md
```
