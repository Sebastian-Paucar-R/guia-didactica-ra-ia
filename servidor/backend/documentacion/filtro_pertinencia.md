# Filtro de pertinencia temática del chat

> **Actualización (2026-09-20):** el orden de decisión de abajo es el original. Ahora el filtro clasifica contra `servidor/configuracion/silabo.yaml` (palabras clave → cambio de rol → score → LLM que elige un número de tema o FUERA) y registra unidad y tema de cada consulta. Ver `CLAUDE.md` (sección «Relevance filter») y `servidor/reportes/historial_ajustes.md`.

Antes de generar una respuesta, el tutor decide si la pregunta pertenece a **Normativas de Ingeniería de
Software**. Código: `app/services/pertinencia_service.py`, orquestado en `RAGService.get_answer`
(`app/services/rag_service.py`); temario en `app/core/silabo.py`. Tabla completa de resultados:
[`filtro_pertinencia_resultados.md`](filtro_pertinencia_resultados.md) (generada por
`scripts/evaluar_pertinencia.py`).

## Cómo decide (en este orden)

1. **Excepciones que siempre pasan**, sin filtro: el saludo inicial (`tipo: saludo`) y las preguntas sobre el propio
   tutor (`tipo: funcionamiento`: "¿qué puedes hacer?", "¿qué documentos tienes?", "¿de qué temas me puedes ayudar?").
   Se detectan con expresiones regulares en 2.ª persona (no se usa el LLM). Se responden con el LLM a partir de datos
   reales (documentos indexados y unidades del sílabo), no con un texto fijo.
2. **Score de similitud**: se recuperan los 4 mejores fragmentos con su similitud coseno (0-1). Si el mejor es
   `>= UMBRAL_PERTINENCIA` la pregunta es pertinente y se responde de inmediato, sin llamada extra.
3. **Confirmación con el LLM** (solo si ningún fragmento supera el umbral): llamada corta, temperatura 0, con la lista
   de unidades del sílabo; responde `DENTRO` o `FUERA`. Si no se puede interpretar la respuesta o Ollama falla, se trata
   como `DENTRO` (no se bloquea al estudiante; el prompt de respuesta ya dice con honestidad cuando falta contexto).
   - `DENTRO` → respuesta normal con el RAG (`tipo: respuesta`). Es el caso de temas del sílabo sin documento
     (Scrum, DORA, TDD…).
   - `FUERA` → **no se llama al LLM de respuesta**. Se genera una redirección (`tipo: redireccion`).

### Redirección

Dos llamadas cortas, ninguna con frases predefinidas:

1. *Selección de temas* (temperatura 0): el LLM elige, por número, los temas del sílabo con relación clara y directa
   con la pregunta, o `NINGUNO`. Existe para no forzar conexiones absurdas ("receta de pastel" → "gestión de riesgos").
2. *Redacción* (`PROMPT_REDIRECCION`, temperatura 0.9): reconoce la pregunta, explica que el enfoque es Normativas de
   Ingeniería de Software, propone los temas elegidos (si no hay ninguno, invita en general a dos o tres áreas del
   temario) y termina con una pregunta para retomar. La variación viene del LLM y de la temperatura.

Cada decisión se registra en el log del servidor: `[FILTRO] decision=... score=... umbral=... llm=... pregunta=...`.
`FILTRO_PERTINENCIA_ACTIVO=false` lo desactiva. El JSON de `/api/v1/chat` incluye `tipo`
(`saludo | funcionamiento | sin_documentos | respuesta | redireccion | error`).

## Umbral: `UMBRAL_PERTINENCIA = 0.62`

Constante en `app/core/config.py` (sobrescribible con la variable de entorno `UMBRAL_PERTINENCIA`). Se calibró con
`python scripts/calibrar_umbral.py` (índice temporal con los documentos reales y los embeddings reales, sin LLM):

| Grupo | Preguntas | Mejor score: mín / mediana / máx |
|---|---|---|
| Dentro del temario | 16 | 0.416 / 0.631 / 0.816 |
| Fuera del temario | 18 | 0.308 / 0.440 / 0.610 |

Los rangos **se solapan** (`all-MiniLM-L6-v2` es un modelo modesto en español): "teoría de la relatividad" saca 0.610 y
"no entiendo lo de mantenibilidad en la 25010" saca 0.416. Ningún umbral separa limpiamente, así que el score se usa
como primer filtro barato y el LLM arbitra la zona gris:

| Umbral | Dentro que van al LLM | Fuera que pasan sin filtro (muestra de 18) |
|---|---|---|
| 0.40 | 0/16 | 12/18 |
| 0.50 | 2/16 | 5/18 |
| 0.56 | 5/16 | 2/18 |
| 0.60 | 5/16 | 1/18 |
| **0.62** | **7/16** | **0/18** |
| 0.65 | 9/16 | 0/18 |

Se eligió 0.62: es el primer valor con el que ninguna pregunta fuera del temario se cuela sin pasar por el LLM, con
margen de solo 0.01 sobre el máximo observado (0.610). El costo es que cerca de la mitad de las preguntas del temario
(las de menor score) hacen una llamada extra de ~0.3 s al clasificador. Se prefirió eso a un umbral más alto (más
llamadas) o más bajo (deja pasar preguntas fuera de tema). Además, el índice ahora usa **métrica coseno** (antes L2) para
que el score sea comparable y esté entre 0 y 1.

## Resultados (servidor real + Ollama `llama3.2`)

Ejecutado con `scripts/evaluar_pertinencia.py` sobre `POST /api/v1/chat` (55 consultas):

| Grupo | Esperado | Aciertos | Pasan por el LLM | Tiempo medio |
|---|---|---|---|---|
| Saludo ("hola") | `saludo` | 1/1 | 0 | 0 s |
| Sobre el tutor (5) | `funcionamiento` | 5/5 | 0 | 9.9 s |
| **Dentro del temario (24)** | `respuesta` | **24/24** | 10 | 14.0 s |
| **Fuera del temario (22)** | `redireccion` | **22/22** | 22 | 5.5 s |
| Casos límite (3, sin etiqueta) | libre | – | 3 | 5.1 s |

- Las 24 preguntas dentro incluyen 14 de temas con documento (ISO 9001, 25010, 27001/27002, 31000, 12207, 33000,
  29110, SGSI, certificación, auditorías, mejora continua, QA) y 10 del sílabo **sin documento** indexado (Scrum, DORA,
  deuda técnica, TDD, puntos de función, incidentes, CI/CD, CMMI, V&V, backlog). Estas últimas no se redirigen: pasan
  a responder con el RAG (que dirá con honestidad si le falta contexto).
- Las 22 fuera cubren cocina, deportes, geografía, cine, matemáticas, salud, programación básica, física, historia,
  turismo, música, mascotas, poesía, finanzas y compras.
- Casos límite: "proteger mi cuenta de Instagram", "qué es un pull request en Git" y "organizar mi tiempo de estudio"
  fueron redirigidos (decisión razonable, pero discutible para los dos primeros por su cercanía a seguridad y CI/CD).
- La evaluación es una foto de una ejecución; el LLM no es determinista en la redacción.

### Historial de ajustes (honestidad sobre el proceso)

1. **Primera corrida**: 15/16 dentro y 18/18 fuera. Falló "¿Cómo se hace una auditoría interna de calidad?"
   (score 0.608, el clasificador dijo `FUERA` → redirección errónea de una pregunta del temario).
2. Se probó el clasificador **aislado** sobre 24 preguntas dentro (8 nuevas, no vistas al diseñar el arreglo) y 18 fuera:
   con el prompt inicial fallaba en 7 de las 24 dentro (auditoría, SGSI, mejora continua, incidentes, 27001 vs 27002…;
   varias nunca llegan a él en el flujo real porque su score supera el umbral). Se reescribió el prompt con un criterio
   inclusivo y "ante la duda, `DENTRO`": pasó a 0 errores sobre ese conjunto.
3. Las redirecciones iniciales eran largas, forzaban conexiones absurdas y en 1 de 3 corridas "respondían" la receta.
   Se añadió el paso de selección de temas y se puso la prohibición de responder al principio del prompt.
4. La corrida final (tabla de arriba) usa los prompts ya ajustados y las preguntas ampliadas; por eso el 24/24 y 22/22
   **no es una medida independiente del ajuste**: 8 preguntas dentro y 4 fuera se añadieron después de la primera
   corrida para reducir el sobreajuste, y ambas pasaron sin cambios adicionales de prompt.

### Calidad de las redirecciones y limitaciones conocidas

Cumplen la estructura pedida (reconocen la pregunta, explican el enfoque, proponen temas, cierran con una pregunta) y
varían en la redacción (ver la sección de variación del archivo de resultados: misma pregunta, tres redacciones
distintas). Con `llama3.2` (3B) hay defectos que un modelo mayor probablemente corregiría:

- **Fuga de contenido ocasional**: en "Explícame la teoría de la relatividad" la redirección incluyó una frase que
  define el tema antes de redirigir (1 de 25 redirecciones de la corrida final; el LLM de *respuesta* nunca se llamó).
- Suele alargarse (4-6 oraciones frente a las 3-4 pedidas) y repite el arranque "Me parece que estás buscando…".
- Algún tono forzado ("Buenos días, ¿cómo estás?", "¿De qué hablas, amigo?", proponer "una sesión de clase").
- El selector de temas es **conservador**: casi siempre responde `NINGUNO`, por lo que la mayoría de las redirecciones
  proponen áreas generales (unidades 1, 2, 3, 4) y no temas específicos. Aflojarlo hizo que el modelo inventara
  conexiones (p. ej. "organizar mi tiempo" → puntos de función), así que se dejó estricto.
- El clasificador y el selector no son deterministas al 100 % aunque la temperatura sea 0.

Mejoras posibles (no hechas): un modelo de embeddings multilingüe (separaría mejor los scores y permitiría un umbral
más bajo), un LLM mayor para redactar, y una verificación posterior de la redirección (que no contenga contenido de la
pregunta) con reintento.

## Cómo reproducir

```
# desde servidor/backend, con Ollama corriendo
python scripts/calibrar_umbral.py            # scores por pregunta y tabla de umbrales (sin LLM)
python -m pytest                             # 85 tests (LLMs y embeddings falsos)

# servidor en marcha con PYTHONUTF8=1 y su salida en un log
python scripts/evaluar_pertinencia.py --log ruta/server.log --salida resultados.md
```
