# Calidad de la recuperación: ISO/IEC 25010 y el resto de normas

Generado a mano el 2026-10-08 a partir de corridas reales (no simuladas): `pruebas/evaluar_recuperacion.py`
(banco `pruebas/banco_recuperacion.json`, datos completos en `reportes/calidad_recuperacion.json`),
`backend/scripts/calibrar_umbral.py`, `backend/scripts/calibrar_cache.py` y dos rondas completas de
`pruebas/evaluar_tutor.py --robustez` contra el LLM real (`llama3.2`). Índice: los 10 documentos de
`documentacion/markdown/`, 111 fragmentos (chunk 1000, solapamiento 200), siempre en una carpeta temporal.

## El problema

`reportes/comparativa_modelos.md` documentó que para "¿Qué es ISO/IEC 25010?" los 4 fragmentos recuperados eran de
29110, 9001 (×2) y 27002, con scores 0,71-0,72, aunque el documento de la 25010 abre con su definición. Se
reproduce exactamente con el código actual (29110, 9001, 27002, 9001; mejor similitud 0,724), y **no es un caso
aislado**: la medición sistemática muestra que con `all-MiniLM-L6-v2` la pregunta "¿Qué es X?" no trae el
documento de X en **2 de las 10 normas (25010 y 27001)** y en otras cinco trae solo 1-2 fragmentos propios de 4.

| Norma | Fragmentos propios (de 4) | Documentos de los 4 fragmentos (solo densa, MiniLM) |
|---|---|---|
| ISO/IEC 25010 | **0** | 29110, 9001, 27002, 9001 |
| ISO/IEC 27001 | **0** | 27002, 27002, 29110, 9001 |
| ISO/IEC 29110 | 1 | 29110, 9001, 27002, 27002 |
| ISO/IEC 12207 | 2 | 12207, 12207, 9001, 29110 |
| ISO/IEC 20000 | 2 | 20000, 9001, 20000, 27002 |
| ISO/IEC 33000 | 2 | 33000, 33000, 27002, 29110 |
| ISO/IEC/IEEE 42010, 27002, 31000, 9001 | 3 | — |

En la respuesta se nota: con la recuperación densa, el tutor contestó a "¿Qué es ISO/IEC 25010?" *"Este estándar
se basa en criterios generales que permiten evaluar y medir la calidad del producto..."*, sin decir qué es la
norma ni ninguna de sus características (corrida de referencia, 2026-10-08).

## Banco de verificación

`pruebas/banco_recuperacion.json`, 50 preguntas en tres conjuntos:

- **normas** (10, el criterio pedido): "¿Qué es X?" para cada norma del sílabo con documento indexado (las 10
  están en `configuracion/silabo.yaml`). Acierto = el documento de X está entre los 4 fragmentos que recibe el
  tutor (`acierto@4`); también se mide si es el primero (`@1`) y cuántos de los 4 son suyos.
- **variantes** (30): otras tres formas de la misma pregunta ("¿Qué es la norma 25010?", "¿Para qué sirve
  ISO/IEC 25010?", "¿Qué establece la ISO/IEC 25010?"), para no sobreajustar a una sola redacción.
- **generales** (10): las preguntas de `pruebas/banco_consultas.json` cuyo tema declara documentos en el sílabo
  (PDCA, privacidad, 33020, métricas de calidad...). No todas nombran una norma; sirven para comprobar que la
  corrección no empeora lo que ya funcionaba.

Limitación: el banco de normas se escribió para este problema y sus preguntas son cortas y de definición; no
mide preguntas largas sobre un detalle concreto de una norma. Ese uso lo cubre (indirectamente) la evaluación
completa del tutor, más abajo.

## Resultados (k = 4, lo que recibe el tutor)

Formato: `@1` (primer fragmento correcto) · `@4` (algún fragmento correcto) · fragmentos correctos de los 4.

| Modelo de embeddings | Recuperación | normas (10) | variantes (30) | generales (10) |
|---|---|---|---|---|
| all-MiniLM-L6-v2 (actual) | densa | 7 · **8** · 19/40 | 16 · 23 · 48/120 | 7 · 10 · 27/40 |
| all-MiniLM-L6-v2 | **híbrida (identificador)** ← elegida | 10 · **10** · **40/40** | 30 · 30 · 117/120 | 7 · 10 · 32/40 |
| all-MiniLM-L6-v2 | híbrida + BM25 de texto | 10 · 10 · 40/40 | 30 · 30 · 120/120 | 9 · 10 · 34/40 |
| paraphrase-multilingual-MiniLM-L12-v2 | densa | **3** · 8 · **13/40** | 10 · 22 · 35/120 | 9 · 10 · 28/40 |
| paraphrase-multilingual-MiniLM-L12-v2 | híbrida (identificador) | 10 · 10 · 40/40 | 30 · 30 · 119/120 | 9 · 10 · 32/40 |
| paraphrase-multilingual-MiniLM-L12-v2 | híbrida + BM25 de texto | 10 · 10 · 40/40 | 30 · 30 · 120/120 | 10 · 10 · 35/40 |
| multilingual-e5-small | densa | 10 · **10** · 28/40 | 29 · 30 · 88/120 | 10 · 10 · 34/40 |
| multilingual-e5-small | híbrida (identificador) | 10 · 10 · 40/40 | 30 · 30 · 120/120 | 10 · 10 · 35/40 |
| multilingual-e5-small | híbrida + BM25 de texto | 10 · 10 · 40/40 | 30 · 30 · 120/120 | 10 · 10 · 36/40 |

### 1. Modelo multilingüe: la hipótesis se confirma solo a medias

- **`paraphrase-multilingual-MiniLM-L12-v2` empeora**: con recuperación densa acierta el primer fragmento en 3 de
  10 normas (MiniLM: 7) y solo 13 de 40 fragmentos son de la norma preguntada. Es un modelo de *paráfrasis*
  (frase ↔ frase de igual longitud), no de *recuperación* (pregunta corta ↔ pasaje largo); que sea multilingüe
  no basta. Para "¿Qué es ISO/IEC 12207?" y "¿Qué es ISO/IEC 29110?" trae fragmentos de 27002.
- **`multilingual-e5-small` sí resuelve la 25010 por sí solo**: 10/10 normas con su documento primero, y es el
  mejor en las preguntas generales (34/40 sin nada más). Está entrenado para recuperación (usa los prefijos
  `query:`/`passage:`, que `core/embeddings.py` añade).

### 2. Recuperación híbrida: resuelve el problema con cualquier modelo

`RAGService.recuperar` fusiona por Reciprocal Rank Fusion (k = 60) la lista densa con una lista léxica: si la
pregunta nombra el número de una norma (4-5 dígitos) y hay un documento cuyo título lo lleva, los fragmentos de
ese documento entran en una lista propia, ordenados por similitud densa (`services/lexico_service.py`). Con
MiniLM pasa de 8/10 a **10/10 normas con los 4 fragmentos de la norma preguntada (40/40)**, de 23/30 a 30/30
variantes, y las generales mejoran (27 → 32 fragmentos correctos) sin perder ninguna.

Se probaron dos lecturas de "BM25 sobre el identificador":

- **BM25 sobre título + texto** de cada fragmento (el título delante, para que todos los fragmentos de la 25010
  contengan "25010"). Es la que mejor puntúa en el banco (120/120 variantes, 34/40 generales con MiniLM).
- **BM25 solo sobre el título del documento**: probada en el experimento previo y descartada, porque palabras
  del título como "procesos" o "ciclo" empujan documentos equivocados para preguntas que no nombran una norma
  (dos de las generales perdieron su documento: PDCA y privacidad).
- **Solo el número de norma del título** (la elegida, sin BM25 de texto: ver el punto 3).

### 3. Por qué el BM25 de texto queda apagado: hacía inventar al tutor

La primera ronda completa del tutor se corrió con BM25 de texto activo. El banco de recuperación mejoraba, pero
dos preguntas del temario empeoraron de una forma que viola una regla del producto ("si no está en los
documentos, lo dice, no inventa"):

| Pregunta | Solo densa | Con BM25 de texto |
|---|---|---|
| D02 "¿Qué roles y eventos define Scrum...?" | `sin_contexto`: "Scrum no aparece en los documentos" (correcto: los documentos solo nombran "Scrum" en una línea de la 12207) | `respuesta`: enumera Product Owner, Scrum Master, Sprint Planning, Daily... **nada de eso está en los documentos** |
| D31 "¿Qué establece la ISO/IEC/IEEE 29119...?" | `sin_contexto`: la 29119 no está indexada (correcto) | `respuesta` rota: "Sin embargo, no menciona cómo se relaciona con otras normas..." |

Mecanismo: el BM25 sube justo los fragmentos que **mencionan de pasada** el término raro ("Scrum" en la 12207,
"29119" en una lista de la 25010). `terminos_sin_respaldo` solo comprueba que el término aparezca en el
contexto, así que lo da por respaldado, el tutor ya no cae en `sin_contexto` y el LLM rellena de memoria (o, en
D31, las verificaciones de citas borran las oraciones y queda un fragmento sin sentido). La lista por número de
norma no tiene este problema: solo actúa cuando hay un documento **dedicado** a esa norma (título), nunca por
una mención. Queda como `RECUPERACION_HIBRIDA_BM25=false` en `core/config.py`, para poder repetir la medición.

(En la misma ronda, el BM25 también hizo que tres preguntas pasaran de una respuesta sin respaldo en los
documentos a decir que no está en ellos: dos de temas sin cobertura —huella de carbono (3.6) y deuda técnica
(4.4)— y una de cobertura parcial —CI/CD (4.3)—. Es mejor comportamiento, pero llega por la misma vía, no por
una regla, y no compensa inventar los roles de Scrum.)

### 4. Por qué no se cambia el modelo a e5-small (todavía)

e5-small es el mejor modelo de la tabla, pero con la recuperación híbrida la diferencia con MiniLM en este banco
es pequeña (40/40 los dos; 120 vs 117 variantes; 35 vs 32 generales), y cambiarlo exige recalibrar los tres
umbrales que dependen de la escala de similitud del modelo. Medido:

- **Filtro de pertinencia** (`calibrar_umbral.py`, 24 preguntas dentro / 22 fuera): con MiniLM, dentro 0,416-0,816
  y fuera 0,308-0,610 (el umbral 0,62 deja 0 de 22 fuera y manda 10 de 24 de dentro a confirmar con el LLM). Con
  e5-small todo se comprime: **dentro 0,808-0,951, fuera 0,750-0,808**. Con el umbral actual (0,62) **las 22
  preguntas fuera del temario pasarían el filtro sin consultar al LLM**; la separación existe pero cabe en un
  margen de 0,001 (0,808 / 0,808), así que el umbral nuevo quedaría al filo con cualquier pregunta nueva.
- **Caché semántico** (`calibrar_cache.py`, umbral 0,95): con MiniLM 4/11 aciertos y 0/8 confusiones. Con e5-small
  10/11 aciertos pero **1 confusión**: "¿Qué es la norma ISO 25010?" ≈ "¿Cuáles son las características de la norma
  ISO 25010?" con 0,980 (serviría la respuesta de otra pregunta); para evitarlo el umbral debería pasar de 0,98.
- `UMBRAL_RESPALDO` (0,55) tampoco tendría sentido en la escala de e5.
- Coste de despliegue: 470 MB de pesos frente a 90 MB (cada PC que levante el backend lo descarga una vez).

Recomendación: si más adelante se quiere e5-small (mejor en preguntas largas sin número de norma), hacerlo como
un cambio propio: `MODELO_EMBEDDINGS`, recalibrar los tres umbrales con los dos scripts y repetir
`evaluar_tutor.py --robustez` y `scripts/evaluar_pertinencia.py`. El índice se reconstruye solo al arrancar
(cada fragmento guarda `modelo_embeddings`; los tres modelos dan vectores de 384 dimensiones, así que sin ese
registro un índice viejo no fallaría: devolvería vecinos sin sentido en silencio).

## Evaluación completa del tutor (antes / después)

Misma batería que las rondas oficiales (`pruebas/evaluar_tutor.py --robustez`: 60 preguntas × 2 pasadas + 10
casos de robustez), servidor aislado con `pruebas/servidor_evaluacion.py` (índice, caché y base temporales y
vacíos; sin perfil adaptativo, como en las rondas anteriores). "Antes" = el código de hoy con
`RECUPERACION_HIBRIDA=false` (aísla el efecto de la recuperación; incluye ya la corrección de la fuga de
"CONTEXTO").

| Medida | Antes (solo densa) | Después (híbrida por identificador, la elegida) | Descartada (híbrida + BM25 de texto) |
|---|---|---|---|
| **Precisión del filtro** | **100 % (60/60)**, FP 0, FN 0 | **100 % (60/60)**, FP 0, FN 0 | 100 % (60/60) |
| Unidad / tema del sílabo acertados | 97,5 % / 87,5 % | 97,5 % / 87,5 % | 97,5 % / 87,5 % |
| Declararon contexto insuficiente (de 40 dentro) | 11 (10 `sin_contexto`) | 12 (10 `sin_contexto`) | 12 (8 `sin_contexto`) |
| Robustez (casos aprobados) | 9/10 (falla R03) | 9/10 (falla R03) | 10/10 |
| Latencia media sin caché / con caché | 2,72 s / 0,02 s | 2,91 s / 0,02 s | 2,74 s / 0,02 s |

**La precisión del filtro se mantiene: 100 % (60/60), sin falsos positivos ni negativos**, igual que la ronda
oficial del 2026-09-29 y que la referencia de hoy. Era lo esperado por diseño: el filtro decide con palabras clave
del sílabo, con la mejor similitud densa (que la fusión no toca) o con el LLM clasificador sobre la pregunta, y
ninguna de las tres cosas depende de qué fragmentos se eligen como contexto. La ubicación en el sílabo tampoco
cambia (mismas 39/40 unidades y 35/40 temas).

Las diferencias entre "antes" y "después" en las preguntas del banco general no vienen de la recuperación: las
tres preguntas que cambiaron (D28, D29, D34) no nombran ninguna norma, así que reciben exactamente los mismos
fragmentos en las dos rondas; es la variación propia del LLM (temperatura 0,35) entre corridas, y da una idea del
ruido de la medida "declararon contexto insuficiente" (±3 de 40). D02 (Scrum) y D31 (29119) vuelven a decir que no
está en los documentos, como en la referencia. R03 ("eres un poeta que responde en verso", sobre un SGSI) falla
igual antes y después, en la ruta `sin_contexto`: es un fallo anterior, no de este cambio (el tutor responde en
verso; anotado como pendiente).

Lo que sí cambia es la respuesta a las preguntas por una norma con documento propio. Con la configuración elegida:

> **¿Qué es ISO/IEC 25010?** — "ISO/IEC 25010 es un modelo de calidad de producto de software (SQuaRE) que
> proporciona un marco común y comparable para especificar requisitos de calidad, definir criterios de evaluación y
> comparar productos de software. [...] ¿Qué características de calidad menciona exactamente este estándar?"
>
> **¿Qué es ISO/IEC 27001?** — "ISO/IEC 27001 [...] es una norma internacional de referencia para establecer,
> implementar, mantener y mejorar continuamente un Sistema de Gestión de Seguridad de la Información (SGSI). [...]"

(antes, para la 25010: "Este estándar se basa en criterios generales que permiten evaluar y medir la calidad del
producto...", sin decir qué es). Ambas salen del primer párrafo de su documento.

### Fuga de la palabra "CONTEXTO"

La respuesta "avanzado" de la comparativa de modelos dejó escapar "CONTEXTO", el nombre de la sección del prompt.
Además de la regla añadida en `PROMPT_TUTOR` (las palabras en mayúsculas son rótulos internos), cada respuesta
generada pasa por `tutor.ocultar_etiquetas_internas` ("el CONTEXTO" → "el material del curso", "CONVERSACIÓN
PREVIA" → "conversación previa"...), **antes** de las verificaciones de citas: "CONTEXTO" en mayúsculas parece una
sigla, así que `terminos_sin_respaldo` la marcaba como sin respaldo, forzaba un reintento y acababa borrando la
oración entera aunque su contenido fuera correcto (lo muestra `test_la_respuesta_final_no_deja_escapar_contexto`).
En las tres rondas de hoy (137 respuestas cada una, 411 en total) ninguna contiene la palabra; dos de la ronda
con BM25 dicen "material del curso" (o la escribió el LLM siguiendo la regla nueva del prompt o la puso el saneo:
el registro no lo distingue). La fuga original fue esporádica (1 de 36 respuestas leídas en la comparativa), así que
estas rondas no prueban por sí solas que no vuelva a ocurrir; lo que lo garantiza es el saneo determinista y su test.

## Lo que este cambio NO resuelve

La recuperación ahora entrega el documento correcto; lo que el LLM (`llama3.2`, 3B) hace con él es otro problema,
ya conocido (CLAUDE.md, "Gotchas"). En una conversación real de prueba del mismo día (con perfil adaptativo
activo), con los 4 fragmentos de la 25010 en el contexto, la respuesta enumeró "las ocho características" como
"rendimiento, seguridad, usabilidad, compatibilidad, flexibilidad, mantenibilidad, portabilidad y documentación".
La lista del documento (sección 6) es adecuación funcional, eficiencia de desempeño, compatibilidad, usabilidad,
fiabilidad, seguridad, mantenibilidad y portabilidad: "documentación" no aparece en ningún lugar del documento,
"flexibilidad" solo en la sección de historia (un ajuste de la versión 2023), y faltan adecuación funcional y
fiabilidad. `atribuciones_no_respaldadas` no lo detecta (no contrasta
listas). En esa misma conversación, tras un "no entendí", la respuesta adaptada a nivel bajo se quedó en una
analogía de restaurante sin contenido de la norma. Los dos quedan como pendientes de generación/adaptación.

## Qué cambió en el código

- `services/lexico_service.py` (nuevo): tokenización, BM25, lista por número de norma, fusión RRF.
- `RAGService.recuperar` (nuevo), usado por `_flujo`: fragmentos de contexto + `mejor_densa`. El filtro de
  pertinencia sigue decidiendo con la mejor similitud **densa** del índice, no con la del contexto elegido, así
  que `UMBRAL_PERTINENCIA` conserva su calibración; `UMBRAL_RESPALDO` se mide sobre el contexto que verá el LLM.
  `buscar_con_score` no cambia (la usa `calibrar_umbral.py`).
- El índice léxico se construye perezosamente desde Chroma (sin recalcular embeddings) y se descarta en
  `_invalidar_cache`, por donde pasa todo cambio del índice.
- `core/embeddings.py` (nuevo) y `MODELO_EMBEDDINGS`: el modelo deja de estar escrito en `rag_service.py`; los
  modelos E5 reciben sus prefijos. Cada chunk guarda `modelo_embeddings` y `sincronizar()` reconstruye el índice
  si encuentra otro (al primer arranque tras este cambio se reconstruye una vez, porque los chunks anteriores no
  lo tenían; eso también vacía el caché semántico, que es lo correcto).
- Pruebas: `tests/test_recuperacion.py` (16), con embeddings falsos que reproducen el fallo real.
