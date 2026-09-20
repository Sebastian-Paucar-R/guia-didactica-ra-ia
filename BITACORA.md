# BITÁCORA

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
