# BITÁCORA

## 2026-09-20 — Caché semántico de respuestas (SQLite) con invalidación y estadísticas

### Qué se implementó
- `services/cache_service.py` (`CacheSemantico`) + integración en `RAGService.get_answer`: embedding de la pregunta (mismo
  MiniLM del RAG), búsqueda por similitud coseno en `servidor/cache_respuestas.db` (SQLite, sin copia en memoria, sobrevive
  a reinicios). Acierto → respuesta guardada sin llamar a ningún LLM, contador de usos +1 y fecha de último uso. Fallo →
  flujo normal y se guarda (pregunta, embedding, respuesta, contexto, fuentes, usos, fechas, tiempo de generación).
- `POST /chat` devuelve `desde_cache` y `tiempo_respuesta_ms`. Nuevo `GET /api/v1/cache/estadisticas`: total de entradas,
  tasa de aciertos, 10 preguntas más repetidas, tiempo promedio ahorrado (estimado) y datos de invalidación.
- **Invalidación total** al cambiar el índice: `indexar_archivo` (documento nuevo/modificado), `reconstruir`
  (`/documentos/reindexar`) y `sincronizar` (documentos borrados/cambiados con el servidor apagado). Contador de versión
  que descarta respuestas generadas mientras el índice cambiaba; si la invalidación falla, el caché queda apagado hasta lograrla.
- Salvaguardas contra respuestas de otra pregunta (el modelo de embeddings no separa bien en español): mismo modo
  (TAREA/PROFUNDIZAR/PUNTUAL por señales, sin LLM), mismos números/siglas y misma negación. Seguimientos dentro de una
  conversación, saludos y preguntas sobre el tutor no pasan por el caché; solo se guardan `respuesta` y `sin_contexto`.
- `scripts/calibrar_cache.py`, `backend/documentacion/cache_semantico.md` (método, calibración y resultados para la tesis).
- 36 tests nuevos (242 en total): cada gancho de invalidación se verificó rompiéndolo a propósito.

### Archivos tocados
`servidor/backend/app/{services/cache_service.py (nuevo), services/rag_service.py, api/v1/endpoints/cache.py (nuevo),
api/v1/endpoints/chat.py, core/config.py, main.py}`, `servidor/backend/scripts/calibrar_cache.py` (nuevo),
`servidor/backend/tests/{test_cache.py (nuevo), conftest.py}`, `servidor/backend/requirements.txt` (numpy),
`servidor/backend/documentacion/cache_semantico.md`, `servidor/.gitignore` (nuevo), `CLAUDE.md`, `BITACORA.md`.

### Resultados (servidor real + Ollama llama3.2 + embeddings reales)
Misma pregunta con tres redacciones: 5 521 ms (generada) → 7,4 ms y 7,4 ms (caché), respuestas idénticas. Persiste tras
reiniciar; subir un documento y reindexar vacían el caché; reenviar el mismo archivo no. Detalle en `cache_semantico.md`.

### Decisión a revisar: umbral 0.95 en vez de 0.92
Con 0.92 el caché confundía "¿Qué es ISO 25010?" con "¿Cuáles son las características de ISO 25010?" (0.927) y devolvía
la respuesta equivocada; con 0.95 no se pierde ningún acierto de la muestra. Solo acierta con cambios de forma (≥0.96);
las reformulaciones de fondo ("dime en qué consiste…", 0.6-0.9) se regeneran. Se vuelve a 0.92 con
`CACHE_UMBRAL_SIMILITUD=0.92`. Muestra pequeña (19 pares): recalibrar si crece el corpus de preguntas.

### Pendiente
- Sin política de expulsión (crece hasta la siguiente invalidación); cambiar de modelo de embeddings exige vaciar el caché a mano.
- Siglas en minúsculas ("que es cmmi") no las distingue la huella; preguntas distintas con estructura casi idéntica podrían
  superar el umbral. Un modelo de embeddings multilingüe permitiría acertar reformulaciones de fondo con seguridad.
- Ni la página de prueba ni la app Flutter muestran `desde_cache` / `tiempo_respuesta_ms` (solo el JSON).
- No hay `.gitignore` raíz: los `.pyc` siguen versionados (el nuevo `servidor/.gitignore` solo cubre el `.db` del caché).

### Siguiente paso sugerido
Acumular consultas reales/simuladas y usar `/cache/estadisticas` para el capítulo de resultados (tasa de aciertos, tiempo
ahorrado); evaluar embeddings multilingües para subir la tasa de aciertos sin falsos positivos.

## 2026-09-20 — Prompt del tutor: intención, memoria conversacional y respuestas calibradas

### Qué se implementó
- Nuevo prompt del tutor (`services/tutor_service.py`): respuesta directa sin preámbulos; modo según la intención del
  estudiante (PUNTUAL: breve + pregunta de reflexión; PROFUNDIZAR: extensa con ejemplo de desarrollo de software; TAREA:
  pasos numerados con pistas, nunca resuelta); tutor inviolable; solo contexto recuperado; citar norma + documento.
- Intención: señales explícitas → pregunta directa (sin LLM) → LLM solo para lo ambiguo (el LLM solo clasificaba mal).
- Memoria por `conversation_id` (`services/memoria_service.py`, en RAM): los seguimientos se reescriben como pregunta
  autónoma antes de recuperar y filtrar. `POST /chat` acepta y devuelve `conversation_id`; la página de prueba y la
  pantalla de chat de Flutter lo guardan y reenvían.
- Términos sin respaldo (Scrum, ISO 29119, CI/CD…) → `tipo: "sin_contexto"`: dice que no está en los documentos y da la
  unidad real del sílabo (`ubicar_en_silabo`), en vez de explicarlo de memoria.
- Verificación de lo generado: normas/años/cláusulas/conteos/siglas sin respaldo (reintento y poda), tarea con <3 pasos
  (hasta 2 reintentos), limpieza de preámbulos, etiquetas `[Documento: …]` y encabezados colgados.
- Ollama: `num_ctx=8192` (el prompt se truncaba con 2048), `num_predict=1024` y `repeat_penalty=1.15` (una respuesta llegó
  a 3 846 palabras en bucle).
- 206 tests. Batería real (`scripts/bateria_tutor.py`) y su historial v1→v8: `servidor/backend/documentacion/prompt_tutor.md`
  y `bateria_tutor_resultados.md`.

### Archivos tocados
`servidor/backend/app/{services/tutor_service.py, services/memoria_service.py (nuevos), services/rag_service.py,
api/v1/endpoints/chat.py, core/config.py, core/silabo.py, static/index.html}`, `servidor/backend/scripts/bateria_tutor.py`,
`servidor/backend/tests/{conftest.py, test_tutor.py (nuevo), test_pertinencia.py}`, `servidor/backend/documentacion/*.md`,
`normativas_app/lib/screens/chat_screen.dart` (conversation_id; `flutter analyze` sin problemas), `CLAUDE.md`, `BITACORA.md`.

### Resultados
Batería de 9 mensajes (6 de los tres tipos de intención + 3 extra): intención detectada 9/9; memoria correcta en los dos
seguimientos; puntuales de 64-75 palabras con pregunta final; tareas C y D con 5 pasos numerados sin entregar el trabajo;
E (ISO 29119) y G (Scrum) dicen que no están en los documentos y señalan la unidad correcta.

### Pendiente
- Defectos de llama3.2 (3B) que persisten: F dijo "7 cláusulas" (la base dice 10; el verificador no lo detecta porque "7"
  aparece en el contexto), citar el documento fuente es irregular, ejemplos de PROFUNDIZAR con detalles inventados,
  preguntas de reflexión a veces poco pertinentes. Ideas: LLM mayor para redactar, reranking, verificación semántica.
- La memoria vive en RAM (se pierde al reiniciar). La latencia depende de la máquina (7-45 s en la última corrida).
- `iniciar_servidor.bat` sigue apuntando a un venv sin el stack.

### Siguiente paso sugerido
Probar un modelo más grande en Ollama con la misma batería y decidir si compensa la latencia; persistir la memoria si se necesita.

## 2026-09-20 — Filtro de pertinencia temática en el chat

### Qué se implementó
- Antes de responder, `RAGService.get_answer` decide si la pregunta es del ámbito (orden: 1) saludo y preguntas sobre el
  propio tutor pasan sin filtro; 2) score de similitud coseno del mejor fragmento vs `UMBRAL_PERTINENCIA`; 3) si ninguno
  lo supera, llamada corta al LLM que responde `DENTRO`/`FUERA` con la lista de unidades del sílabo).
- `FUERA` → no se llama al LLM de respuesta: paso corto que elige temas relacionados (o `NINGUNO`) + redacción por LLM
  con un prompt específico de redirección (temperatura 0.9, sin frases fijas). `tipo: "redireccion"` en el JSON de `/chat`
  (también `saludo | funcionamiento | sin_documentos | respuesta | error`). Log `[FILTRO] ...` por decisión.
- Umbral `UMBRAL_PERTINENCIA = 0.62` en `core/config.py` (env-overridable), calibrado con `scripts/calibrar_umbral.py`.
  El índice Chroma pasó a métrica **coseno** (se reconstruye solo una vez al arrancar): 111 chunks, 10 documentos.
- Temario del sílabo en `core/silabo.py`. Nuevo `services/pertinencia_service.py`. `FILTRO_PERTINENCIA_ACTIVO` para apagarlo.
- 85 tests (LLMs y embeddings falsos). Documentación y resultados: `servidor/backend/documentacion/filtro_pertinencia.md`
  y `filtro_pertinencia_resultados.md`.

### Archivos tocados
`servidor/backend/app/{core/config.py, core/silabo.py (nuevo), services/rag_service.py, services/pertinencia_service.py (nuevo),
api/v1/endpoints/chat.py}`, `servidor/backend/scripts/{calibrar_umbral,evaluar_pertinencia,preguntas_pertinencia}.py` (nuevos),
`servidor/backend/tests/test_pertinencia.py`, `servidor/backend/documentacion/*.md`, `servidor/base_vectorial/`, `CLAUDE.md`, `BITACORA.md`.

### Resultados (servidor real + Ollama llama3.2, 55 consultas)
Saludo 1/1, sobre el tutor 5/5, dentro del temario 24/24 (10 pasaron por el clasificador), fuera del temario 22/22.
Ojo: la primera corrida dio 15/16 dentro (falló "auditoría interna de calidad"); se ajustó el prompt del clasificador y se
amplió la muestra (ver historial en `filtro_pertinencia.md`), así que el 24/24 y 22/22 no es una medida independiente.

### Pendiente
- Fuga ocasional de contenido en la redirección (1/25: definió la teoría de la relatividad); redirecciones largas y de tono
  algo torpe con llama3.2 (3B). Ideas: LLM mayor para redactar, verificación posterior con reintento.
- El selector de temas casi siempre responde `NINGUNO` (conservador a propósito): las redirecciones proponen áreas generales.
- Embeddings `all-MiniLM-L6-v2` solapan mucho los scores en español (por eso el umbral es alto); un modelo multilingüe
  permitiría un umbral más bajo y menos llamadas al clasificador.
- Sin prueba en navegador de la interfaz (no muestra `tipo`); `iniciar_servidor.bat` sigue apuntando a un venv sin el stack.

### Siguiente paso sugerido
Mostrar/medir `tipo` (p. ej. contar redirecciones desde el log `[FILTRO]`) y evaluar un modelo de embeddings multilingüe.

## 2026-09-19 — Carga de documentos con conversión doble y reindexado incremental

### Qué se implementó
- `POST /api/v1/documentos/subir`: uno o varios archivos (PDF, DOCX, PPTX, TXT, MD). Por cada uno guarda
  `documentacion/originales/`, `documentacion/pdf/` y `documentacion/markdown/`; errores por archivo sin abortar el lote.
  Respuesta por archivo: nombre, rutas de las 3 copias, chunks indexados y estado (`indexado` / `omitido_sin_cambios` / `error`).
- `POST /api/v1/documentos/reindexar` (reconstrucción completa) y `GET /api/v1/documentos` (lista + chunks).
- Conversión con librerías solo-pip: `markitdown` (→ Markdown) y `reportlab` (→ PDF). Elección y descartes documentados en `CLAUDE.md`.
- RAG incremental: solo indexa `documentacion/markdown/`; hash SHA-256 por `.md`; metadata `nombre_archivo`, `hash`, `fecha_indexado`;
  hash existente → omite; mismo nombre con hash distinto → reemplaza sus chunks; ids `hash:n` (upsert) ⇒ sin duplicados.
  Al arrancar sincroniza (indexa lo nuevo, poda lo borrado) y reconstruye una sola vez si el store es del esquema anterior.
- Instancia única del RAG (`get_rag_service()`), rutas ya no hard-coded (`core/config.py`).
- Interfaz de prueba (`app/static/index.html`, extraída del f-string de `main.py`): subida múltiple, tarjetas de resultado por archivo
  con enlaces a las 3 copias, botón de reindexado, lista y contador de fragmentos reales.
- Migración: los 10 `.md` de `documentacion/` pasaron a `documentacion/markdown/` (`git mv`), con copia en `originales/` y PDF generado en `pdf/`.
  `base_vectorial/` reconstruida: 744 embeddings duplicados → 111 chunks (10 documentos).
- 31 tests (pytest, embeddings falsos, directorios temporales).

### Archivos tocados
`servidor/backend/app/{main.py, core/config.py, services/rag_service.py, services/conversion_service.py (nuevo),
api/v1/endpoints/{chat.py, documentos.py (nuevo)}, static/index.html (nuevo)}`, `servidor/backend/{requirements.txt, pytest.ini, tests/*}`,
`servidor/documentacion/{markdown,originales,pdf}/`, `servidor/base_vectorial/`, `CLAUDE.md`, `BITACORA.md`.

### Verificación realizada
Tests 31/31; servidor real arrancado con el Python del sistema (sincroniza 10 docs / 111 chunks, reinicios sin duplicar);
subida de un PDF (generado por el conversor, no había ninguno en el proyecto) → indexado, repetido → omitido_sin_cambios, versión modificada →
chunks reemplazados; lote con `.exe`/DOCX corrupto/TXT vacío → solo esos en `error`; `reindexar` → conteo = suma de `markdown/`;
`/chat` responde con contexto correcto; JS de la interfaz ejecutado contra el servidor real con un DOM simulado (no hubo prueba visual en navegador).

### Pendiente
- `iniciar_servidor.bat` activa `backend/venv`, que no tiene el stack RAG (ver Gotchas en `CLAUDE.md`).
- El PDF de DOCX/PPTX es una re-renderización del texto (no copia visual); PDFs escaneados fallan (sin OCR).
- `norma.docx` y `norma.pdf` comparten copias `pdf/`+`markdown/` (gana la última; se avisa en `detalle`).
- `HuggingFaceEmbeddings` de `langchain_community` está deprecado (migrar a `langchain-huggingface`).
- `llama3.2` inventa detalles aunque el contexto sea correcto; los cambios de prompt/regla "no entrega la respuesta completa" no se tocaron.
- Los `.pyc` trackeados siguen sin `.gitignore`.

### Siguiente paso sugerido
Corregir el flujo de arranque (`iniciar_servidor.bat` / venv) y añadir los documentos que faltan del sílabo (29119, 14764, 42001, CMMI) usando la nueva carga.
