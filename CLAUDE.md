# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

"Guía Didáctica Interactiva de Realidad Aumentada con IA para Normativas de Ingeniería de Software" (Spanish-language project; docs, prompts and UI text are in Spanish). The git root is `PROYECTO/` and holds two independent pieces:

- `servidor/` — FastAPI backend: a RAG "Tutor IA" that answers questions about ISO/IEC standards (9001, 12207, 20000, 25010, 27001, 27002, 29110, 31000, 33000, 42010) from Markdown documents, using a local Ollama LLM.
- `normativas_app/` — Flutter client (chat, home, profile, AR scanner screens). Its chat screen POSTs to `http://127.0.0.1:8000/api/v1/chat` (hard-coded in `lib/screens/chat_screen.dart`; an Android emulator would need `10.0.2.2` instead).

The backend has a pytest suite (`servidor/backend/tests/`, run `python -m pytest` from `servidor/backend/`; it uses fake embeddings and temp dirs, so it never touches the real `documentacion/` or `base_vectorial/`). There is no linter config or CI. The Flutter app is still mostly the default project scaffold (its README is the stock template).

## Running the backend

Windows-only workflow (paths are hard-coded, see below). External requirement: an [Ollama](https://ollama.com) server running locally with the `llama3.2` model pulled (`ollama pull llama3.2`).

```
servidor\iniciar_servidor.bat
```

This activates `backend\venv`, sets `PYTHONPATH=backend`, and runs from `servidor/`:

```
python -m uvicorn app.main:app --reload --port 8000 --app-dir backend
```

Paths (`documentacion/`, `base_vectorial/`) are resolved from the location of `app/core/config.py` (see `Settings`), not from the cwd, and can be overridden with the `DOCUMENTACION_DIR` / `BASE_VECTORIAL_DIR` env vars. `GET /` serves the HTML test page `app/static/index.html` (docs list + upload/indexing panel + chat + localStorage history); `POST /api/v1/chat` takes `{message, user_id?}` and returns `{response, context, status}`; `GET /documentacion/{originales|pdf|markdown}/{archivo}` serves a copy of a document (the old `GET /documentacion/{archivo}` still works and looks in `pdf/`, `markdown/`, `originales/`). The document endpoints are described in "Document upload" below.

When running the server with stdout redirected on Windows (e.g. from a script), set `PYTHONUTF8=1`: `chat.py` prints a `→` that raises `UnicodeEncodeError` under cp1252 (a real console is fine).

Flutter app (from `normativas_app/`): `flutter pub get`, `flutter run`, `flutter analyze`, `flutter test`.

## Backend architecture

Layers (all under `servidor/backend/app/`): HTTP layer (`main.py`, `api/v1/endpoints/chat.py`, `api/v1/endpoints/documentos.py`, `api/v1/endpoints/cache.py`) → service layer (`services/rag_service.py`, `services/conversion_service.py`, `services/cache_service.py`) → Chroma vector store + Ollama LLM. The only relational database is the semantic answer cache (SQLite, see "Semantic cache"); there is no auth. Conversation memory lives in RAM per `conversation_id` (`services/memoria_service.py`, lost on server restart); the HTML test page also keeps its chat history in browser `localStorage` (`tutor_history`, plus `tutor_conversation_id`), and `user_id` in `ChatRequest` is accepted but unused.

- `app/main.py` — creates the FastAPI app, CORS `*`, mounts the chat and documentos routers under `/api/v1`, serves `static/index.html` at `/` and the `/documentacion/...` file routes. Settings come from `app/core/config.py` (paths, allowed extensions, `MAX_UPLOAD_MB`); `.env` is empty. A stray copy of `config.py` is tracked at `PROYECTO/backend/app/core/config.py`.
- `app/api/v1/endpoints/chat.py` — the `/chat` endpoint; delegates everything to `RAGService.get_answer` via `get_rag_service()`. `context` in the response is the retrieved text truncated to 1000 chars.
- `app/api/v1/endpoints/documentos.py` — upload / reindex / list endpoints.
- `app/services/rag_service.py` — all RAG logic (LangChain). `get_rag_service()` returns the one shared instance.
- `app/services/pertinencia_service.py` — relevance filter (tutor-question detection, role-change detection, classifier that picks a syllabus topic or FUERA, redirect generation); `app/core/silabo.py` — loads and validates `servidor/configuracion/silabo.yaml` (the single source of the syllabus: 4 units, 27 topics, each with `id`, `nombre`, `unidad`, `palabras_clave`, `archivos`), keyword matching (`buscar_por_palabras_clave`) and the texts inserted into prompts (+ `ubicar_en_silabo`: which unit covers a term). A broken YAML fails at server start (`RAGService.__init__` calls `cargar_silabo()`); path via `SILABO_PATH`.
- `app/services/tutor_service.py` — the tutor prompt and its helpers (student intent, follow-up rewriting, context formatting, checks on what the LLM wrote); `app/services/memoria_service.py` — per-conversation memory.
- `app/services/conversion_service.py` — PDF/Markdown conversion of uploaded files.

`RAGService` request flow for `get_answer(question, conversation_id=None)` (returns `{response, context, tipo, fuentes, desde_cache, tiempo_respuesta_ms}`; `POST /chat` takes `{message, conversation_id?}` and returns `{response, context, status, tipo, conversation_id, desde_cache, tiempo_respuesta_ms, ubicacion}` (`ubicacion` = `{unidad, tema_id, tema, metodo}`: where the question falls in the syllabus and how it was decided, `palabras_clave | llm | embedding`; null for redirects, greetings and questions about the tutor) — if the client sends no id the server creates one and returns it; the HTML page and the Flutter chat screen store and resend it; `tipo` is one of `saludo | funcionamiento | sin_documentos | respuesta | sin_contexto | redireccion | error`):

1. **Greeting shortcut** — if the lowercased question is exactly one of a short list (`hola`, `buenas`, `buenos días`, `buenas tardes`, `hey`, `hi`, `hoola`) a fixed welcome message is returned with no retrieval or LLM call (`tipo: saludo`). This is the only canned reply.
2. **Questions about the tutor itself** (`pertinencia_service.es_pregunta_sobre_tutor`, regexes on 2nd-person phrasing: "¿qué puedes hacer?", "¿qué documentos tienes?", "¿de qué temas me puedes ayudar?"...) skip the filter and are answered by the LLM from real data (indexed document names + syllabus units) — `tipo: funcionamiento`.
3. **Guard** — if the collection has zero chunks it returns a "no documents loaded" message (`sin_documentos`).
4. **Memory** — the last turns of that `conversation_id` are loaded; if the message is a follow-up ("explícame eso mejor", refers to "eso", or is ≤3 words) `reformular_pregunta` rewrites it as a standalone question (only then: rewriting independent questions made the LLM paste history into them). Retrieval and the relevance filter use that standalone question.
5. **Retrieve with score** — top-4 chunks with cosine similarity (`buscar_con_score`).
6. **Relevance filter** — see "Relevance filter" below. Off-topic → `tipo: redireccion`, no answer content. In-topic → the unit/topic is recorded (`[FILTRO] ... unidad=U tema=U.N metodo=...` in the log and `ubicacion` in the response). **Insistence** (`tutor.insistencia`): if the conversation's last turns were TAREA requests the tutor answered and the new message pushes again ("insisto", "sin pistas", "dame la tabla ya terminada, por favor"), the message skips the filter and the cache, retrieval uses the *original* task (`tutor.tarea_original`) and the prompt switches to `INSTRUCCIONES_TAREA_INSISTENTE` (firm, a new more concrete hint, never the solution).
7. **Intent** (`tutor_service.detectar_intencion`): explicit cues first (`resuélveme`, `hazlo por mí` → TAREA; `explícame mejor`, `no entendí`, `ejemplo`, `amplía` → PROFUNDIZAR), then a direct question ("qué es", "cuál es la diferencia", "cuándo aplica"...) → PUNTUAL without any LLM call, and only for imperatives/references a short LLM classification (the small LLM classified almost every conceptual question as PROFUNDIZAR, hence the rules). PROFUNDIZAR retrieves k=6 anchored on the previous student question.
8. **Missing terms** (`terminos_sin_respaldo`) — if the student names a norm number, acronym (CMMI, DORA, CI/CD), mixed-case term (DevOps) or syllabus proper name (Scrum, Kanban) that is not in the retrieved context or document names, the tutor does NOT explain it: `PROMPT_SIN_CONTEXTO` says it is not in the documents and points to the real syllabus unit (`ubicar_en_silabo`) → `tipo: sin_contexto`. A prompt-level warning was not enough with llama3.2.
9. **Generate** — `PROMPT_TUTOR` with the mode text for the intent (PUNTUAL: ≤3 sentences + one short reflection question, appended by the LLM if missing; PROFUNDIZAR: several paragraphs + a software-development example; TAREA: numbered steps with hints, never the finished work) plus a one-line reminder of the mode right before the answer. Context fragments are labelled `[Documento: name — «title»]`. Guard rails on the output: preamble/greeting/apology stripped, pasted document labels replaced by the title, dangling "Referencias:" removed, cut-off sentence trimmed, unsupported ISO numbers/years/clauses/counts/acronyms trigger one retry (then those sentences are removed), a TAREA answer with <3 numbered steps or <45 words is retried (max 2). The LLM is `ChatOllama` with `num_ctx=8192`, `num_predict=1024`, `repeat_penalty=1.15`, temperature 0.35 (without the caps llama3.2 once produced 3,800 words in a loop). Any exception is caught and returned as the response text (HTTP status stays 200, `status: "success"`, `tipo: error`).

## Semantic cache (caché semántico de respuestas)

Before the flow above, `get_answer` looks the question up in `servidor/cache_respuestas.db` (SQLite, git-ignored via `servidor/.gitignore`; no in-memory copy, so it survives restarts). Code: `services/cache_service.py` (`CacheSemantico`), hooks in `rag_service.py`, stats endpoint `GET /api/v1/cache/estadisticas` (`{total_entradas, consultas, aciertos, fallos, tasa_aciertos, preguntas_mas_repetidas (top 10 by usos>0), tiempo_promedio_ahorrado_ms, tiempo_total_ahorrado_ms, umbral_similitud, invalidaciones, ultima_invalidacion, motivo_ultima_invalidacion}`; 503 if `CACHE_ACTIVO=false`). Full method, calibration and measured results: `backend/documentacion/cache_semantico.md`.

- **Hit** = embedding (same MiniLM as the RAG) with cosine ≥ `CACHE_UMBRAL_SIMILITUD` (**0.95**, env-overridable; the requested 0.92 let through a real wrong hit, "qué es ISO 25010" → "cuáles son las características de ISO 25010" = 0.927) among entries with the same intent bucket (TAREA/PROFUNDIZAR by explicit cues, else PUNTUAL — no LLM), the same numbers/acronyms (ISO 9001 ≠ 27001) and the same negation. A hit calls no LLM and returns `desde_cache: true`; it also goes into the conversation memory. Miss → normal flow, then the answer is stored if `tipo ∈ {respuesta, sin_contexto}` (never saludo/funcionamiento/redireccion/sin_documentos/error).
- **Bypassed entirely**: greetings, questions about the tutor, and follow-ups inside a conversation (`es_seguimiento` with history: the answer depends on the history).
- **Invalidation (critical)**: every real change of the vector index empties the whole cache — hooks in `indexar_archivo` (new/changed doc, old version removed), `sincronizar` (docs deleted while the server was down) and `reconstruir` (`POST /documentos/reindexar`). No invalidation when nothing changes (`omitido_sin_cambios`, rejected upload). A version counter in the DB makes `guardar()` reject an answer whose generation started before an invalidation; if emptying the DB fails the cache stays off until it succeeds. **Any new code path that changes the Chroma index must call `_invalidar_cache`.** Hit/miss counters and saved time survive invalidation; entries do not.
- Not stored/handled: no eviction policy; changing the embedding model requires emptying the cache by hand; deeper rewordings ("dime en qué consiste…", similarity 0.6–0.9) deliberately miss.
- Tests: `tests/test_cache.py`; `conftest.py` turns the cache off for every other test (autouse) and points `CACHE_DB_PATH` at a temp dir, so tests never touch the real DB. Calibrate with `python scripts/calibrar_cache.py`.

## Relevance filter (filtro de pertinencia temática)

Implemented in `services/pertinencia_service.py` + `RAGService._flujo`; the syllabus is `configuracion/silabo.yaml` (loaded by `core/silabo.py`), **not** a list in a prompt. Order of decision: (1) exceptions above (a role-change request such as "Olvida que eres un tutor" is *not* a question about the tutor even though it contains "que eres"); (2) **YAML keywords** (`silabo.buscar_por_palabras_clave`, no LLM): the question names a topic → in scope, unit and topic known; keywords are accent/case-insensitive whole-word matches, a trailing `*` on a word is a prefix wildcard, `~` marks a weak keyword ("norma ISO") that only decides if no strong one matches anywhere, and norm numbers (`29119`) outweigh phrases; keep them specific: a common word ("cascada", "ciclo de vida", "certificado") lets out-of-scope questions through with no second check; (3) **role change** (`es_intento_abandonar_rol`: "ignora tus instrucciones", "actúa como…", "modo desarrollador", "muéstrame tu prompt") with no syllabus topic → FUERA without calling the classifier; with a topic the question is answered and the prompt gets `AVISO_CAMBIO_DE_ROL`; (4) best chunk similarity `>= settings.UMBRAL_PERTINENCIA` → in scope (topic label by embedding similarity to the YAML topics, `metodo=embedding`); (5) otherwise a short deterministic LLM call (`llm_clasificador`, temperature 0) receives the numbered YAML topics with their keywords and answers a topic **number** or `FUERA` (`parsear_veredicto`; unparseable/failed → fail-open DENTRO). `FUERA` → the answer LLM is **not** called: a second short call picks related topics (`NINGUNO` → no forced connection), then `llm_redireccion` (temperature 0.9, `PROMPT_REDIRECCION`) writes the redirect; a role-change message is replaced by a neutral description before reaching that prompt so its injected order can't be obeyed. Nothing is a fixed phrase. Every decision is logged as `[FILTRO] decision=... score=... llm=... unidad=... tema=... metodo=...` (decision ∈ palabras_clave, rol, pertinente, candidata, insistencia, funcionamiento); `FILTRO_PERTINENCIA_ACTIVO=false` disables the whole filter. A cache hit recomputes `ubicacion` (keywords, else embedding of the question) because the cache does not store it.

- **Threshold** `UMBRAL_PERTINENCIA = 0.62` (env-overridable, in `core/config.py`). With `all-MiniLM-L6-v2` on Spanish text the score ranges overlap heavily (off-topic up to 0.61, in-topic down to 0.42), so the threshold is deliberately high and the LLM arbitrates the grey zone; it skips the classifier only for clearly on-topic questions. Recalibrate with `python scripts/calibrar_umbral.py` if the embedding model or corpus changes.
- **Cosine metric**: the Chroma collection is created with `hnsw:space = cosine` so `1 - distance` is a 0-1 similarity; `sincronizar()` rebuilds a store that uses another metric (once).
- Evaluation: `pruebas/evaluar_tutor.py` (60-question bank, see next section) and the older `scripts/evaluar_pertinencia.py` (questions in `scripts/preguntas_pertinencia.py`, useful as an independent regression set). Method: `backend/documentacion/filtro_pertinencia.md`.
- `llama3.2` (3B) is weak at this: prompts were tuned iteratively (separate topic-selection step; the rule "do not answer the question" goes first in the redirect prompt; the classifier prompt warns that sharing a word with the syllabus, "integración por partes" vs. "pruebas de integración", does not put a question in scope). A two-step classifier (DENTRO/FUERA first, number after) was tried and rejected: it fixed that case but wrongly redirected 3 legitimate questions. If you change a prompt, the YAML or the model, rerun `pruebas/evaluar_tutor.py` (see "Evaluation and coverage") and `scripts/evaluar_pertinencia.py`.

Ingestion is incremental and only reads `documentacion/markdown/*.md` (see "Document upload" below): split with `RecursiveCharacterTextSplitter` (chunk 1000, overlap 200); embed with HuggingFace `sentence-transformers/all-MiniLM-L6-v2`; persist to Chroma (collection `langchain`). Chunks carry `nombre_archivo`, `hash`, `fecha_indexado`, `source`, `chunk`; the API still doesn't report which standard a chunk came from.

## Evaluation and coverage (`servidor/pruebas/`, `servidor/reportes/`, `servidor/configuracion/`)

- `configuracion/silabo.yaml`: the syllabus (see above). Topic 2.8 is flagged `complementario: true`: ISO 20000/29110/31000/42010 are not in the official syllabus but their documents are indexed, so they stay in scope. To add a topic, add it there (unique `id`, existing `unidad`); to back it with a document, upload it and list it in `archivos`.
- `pruebas/auditar_cobertura.py` → `reportes/cobertura_silabo.md` (+ `.json`): for each topic, searches its keywords in the text actually **indexed** in Chroma and reports `cubierto | parcial | sin cobertura` (criteria in the report). Topics without coverage are the ones the tutor cannot answer and will say so (`tipo: sin_contexto`). It reads a temporary copy of `base_vectorial/`: opening Chroma rewrites `chroma.sqlite3` and the `.bin` files, and that directory is versioned in git.
- `pruebas/banco_consultas.json` (40 in-syllabus, 10 per unit, each with its expected `unidad` and `tema_id`; 20 out: sports, politics, other subjects, complete-homework requests, role-abandon attempts) and `pruebas/evaluar_tutor.py` → `reportes/evaluacion_tutor.{json,md}`: filter accuracy (positive = accepted as in scope), false positives/negatives, mean latency with/without cache (two passes; hits are `desde_cache: true`), how many in-syllabus answers declared insufficient context, unit/topic accuracy. `--robustez` also runs `pruebas/casos_robustez.json` (role change, invented norms, insistence). **Its automatic robustness verdicts are heuristics: read the conversations in the JSON.** They said 9/9 while a manual read showed the tutor answering as a pirate and inventing attributions.
- Run it against a server with a clean cache and a copy of the index, so neither the real cache nor `base_vectorial/` is touched: from `servidor/`, `BASE_VECTORIAL_DIR=<copy> CACHE_DB_PATH=<new file> PYTHONUTF8=1 python -m uvicorn app.main:app --app-dir backend` (PYTHONPATH=backend), then `python pruebas/evaluar_tutor.py --robustez`. The cache is not invalidated by prompt changes, so an old cache DB would replay old answers (an off-topic answer, once cached, is served again).
- The bank was written before the first run and used to tune afterwards, so its score is a development score, not an independent one; `scripts/evaluar_pertinencia.py` (46 older questions) is the independent check.

## Document upload (conversión doble + reindexado incremental)

`documentacion/` (under `servidor/`) has three folders, filled per uploaded file: `originales/` (as uploaded), `pdf/` (PDF copy) and `markdown/` (`.md` copy). If the original is a PDF the PDF copy is the same file; if it is `.md` the Markdown copy is the same file. Only `markdown/` is indexed.

- `POST /api/v1/documentos/subir` — multipart, field `archivos` (alias `files`), one or many of PDF/DOCX/PPTX/TXT/MD. Each file is processed independently (a failure never aborts the batch). Response: `{resultados:[{nombre, rutas:{original,pdf,markdown}, chunks_indexados, estado, detalle}], resumen}` with `estado ∈ indexado | omitido_sin_cambios | error`; paths are relative to `servidor/`. The upload is converted from a staging dir and only promoted to `originales/` if conversion succeeds, so rejected/corrupt files never land there or overwrite a valid original.
- `POST /api/v1/documentos/reindexar` — maintenance: `delete_collection()` + full re-index of `markdown/`.
- `GET /api/v1/documentos` — indexed/pending docs with chunk counts (feeds the test page).

Incremental indexing (`RAGService.indexar_archivo`): SHA-256 of the `.md` bytes; chunk ids are `f"{hash}:{n}"` and are upserted, so a chunk can never be duplicated. Hash already in Chroma → `omitido_sin_cambios`; same `nombre_archivo` with a different hash → new chunks are added first, then the old ones are deleted. At startup `sincronizar()` indexes new/changed files, prunes chunks of files no longer in `markdown/`, and — if it finds chunks without a `hash` (pre-upgrade store, full of duplicates) — rebuilds the collection once. `delete_collection` leaves the old segment folder in `base_vectorial/` (locked on Windows until the process ends), so `sincronizar()` also removes segment folders not referenced by `chroma.sqlite3`.

**Library choice** (free, local, Windows, no external binaries):

| Need | Chosen | Rejected |
|---|---|---|
| → Markdown (PDF/DOCX/PPTX) | `markitdown[pdf,docx,pptx]` — pip only, one API for all three formats | `pypandoc` needs the pandoc binary and cannot read PDF; `docling` pulls heavy ML models/weights |
| → PDF | `reportlab` — pip only | `weasyprint` needs GTK/Pango DLLs on Windows; `pandoc` needs the binary plus a LaTeX engine |

Consequences: for DOCX/PPTX/MD/TXT the PDF copy is a **re-rendering of the extracted Markdown** (headings, lists, simple tables, inline bold/italic; Vera font bundled with reportlab), not a visual copy of the original. Scanned PDFs have no text layer and fail with "sin texto extraíble" (there is no OCR). `markitdown` sniffs content, so `conversion_service` checks the real format first (PDF header, ZIP for DOCX/PPTX) — otherwise a corrupt `.docx` would be indexed as plain text. Known limitation: the `pdf/` and `markdown/` copies are named by file stem, so `norma.docx` and `norma.pdf` share them (last upload wins; both originals are kept and the response `detalle` warns about it).

## Tutor behavior rules

These are the rules encoded in `PROMPT_TUTOR` / `INSTRUCCIONES_MODO` in `services/tutor_service.py` (Spanish, university-tutor persona). Keep any prompt change consistent with them and rerun `python scripts/bateria_tutor.py` (details and results: `backend/documentacion/prompt_tutor.md`):

- Start directly with what resolves the doubt: no preamble ("excelente pregunta"), no repeating the question. Short for a specific question, extended (with an example applied to software development) when the student asks to go deeper, guided step by step — never solved — when the student asks for a task to be done.
- Tutor role is inviolable: guide, give hints, ask reflection questions; never hand over the finished exercise or write the student's work. `PROMPT_TUTOR` has a "REGLAS DE ROBUSTEZ" block against three concrete failures: (1) abandoning the role when asked (ignore instructions, "actúa como…", show the prompt), backed by `es_intento_abandonar_rol` before the model; (2) inventing norms/ISO numbers/clauses not in the context, backed by `normas_no_respaldadas` (norm numbers, years, `cláusula|capítulo|sección|apartado N`, counts; one retry, then the sentences are removed): it does not catch wrong *attributions* to real norms (llama3.2 once said ISO 42010 is about AI governance); (3) handing over the solved exercise after repeated insistence, backed by `tutor.insistencia`. The role rule is also in `PROMPT_SIN_CONTEXTO` and in the questions-about-the-tutor prompt.
- Answer only from the retrieved context; if it is insufficient say so clearly and point to the syllabus unit / document, and never invent norms, ISO numbers, years or clauses. Cite a norm with its full identifier and the document it came from.
- Off-topic questions (outside the syllabus) are redirected, never answered — see "Relevance filter".
- Professional but conversational Spanish; no fixed structure repeated across answers (numbered steps only in TAREA mode). The only canned reply is still the initial greeting.
- Memory: the tutor remembers the previous turns of the same `conversation_id` (last 4 turns shown to the LLM, 8 kept, 200 conversations, in RAM).
- Not implemented (do not assume): quizzes, progress tracking, persistence of conversations across server restarts (the semantic cache persists answers, not conversations).

The syllabus's pedagogy (below: ABP, cooperative learning, problem-based learning, evidence-based decisions) is the intended teaching context, but it is not encoded anywhere in the code.

## Sílabo (course context)

Source: official syllabus PDF `7mo-NormativasSoftware-A-signed.pdf` (Universidad Politécnica del Carchi, Carrera de Computación), the course this tutor supports.

- **Asignatura:** Normativas de Ingeniería de Software — código `0611ANIS7UP-AJ2025`, nivel 07, unidad profesional, presencial, paralelo A-M, PAO 2026 B. Prerequisite: Ingeniería de Software. 144 h total (48 contacto docente, 16 práctico-experimental, 80 autónomo). Classes 17 Aug – 2 Dec 2026 (Mon 10–12, Wed 11–13).
- **Resultado de aprendizaje:** manage software projects applying appropriate methodologies and standards to ensure quality across all development phases; apply metrics for planning, design, development, deployment and maintenance; apply segregation of duties (roles/profiles for using and administering software).
- **Evaluación (4 × 25 % = 10 pts):** contacto con el docente, evaluación sumativa, aprendizaje autónomo, práctico-experimental. Sumativas: Parcial 1 (Units I + II), Parcial 2 = team "auditoría integral" (process, quality, metrics, testing, deployment, maintenance, roles, improvement plan).
- **Metodologías:** ABP (project-based), aprendizaje cooperativo, aprendizaje basado en problemas; institutional pedagogical model based on andragogía, constructivism and critical thinking. Formative research project: a prototype built under a normative/quality framework with a chosen methodology, metrics and experimental validation.
- **Unidades y contenidos:**
  1. *Aplicación de metodología de desarrollo de software* — predictive/iterative/agile/hybrid frameworks; Scrum, Kanban, Lean; agile requirements (backlog, user stories, acceptance criteria); SDLC; DevOps/DevSecOps; process governance and continuous improvement. Prácticas 1–2 (methodology selection, agile simulation).
  2. *Normativas de desarrollo y calidad del software* — ISO/IEC/IEEE fundamentals (standards, certification, accreditation, audit, compliance); ISO 9001; ISO/IEC/IEEE 12207; process maturity (CMMI, ISO/IEC 330xx); ISO/IEC 25000 (SQuaRE) / 25010; security, privacy and AI (ISO/IEC 27001, secure development, ISO/IEC 42001, AI governance). Prácticas 3–4.
  3. *Métricas de gestión de proyectos de software* — measurement basics (KPIs, baselines); size/effort/estimation (function points, story points, velocity); product-quality metrics (25010); agile/flow metrics (lead/cycle time, WIP, CFD); DevOps metrics (DORA: deploy frequency, lead time for changes, change failure rate, recovery time); UX/security/sustainability metrics and dashboards. Prácticas 5–6.
  4. *Gestión de pruebas, implementación y mantenimiento* — V&V and test levels; ISO/IEC/IEEE 29119; TDD, automation, static analysis, quality gates; CI/CD, configuration management, containers; maintenance and evolution (ISO/IEC/IEEE 14764 types, refactoring, technical debt); operation, observability, incident management. Práctica 7.
- **Bibliografía clave:** Sommerville (Ingeniería de software), Pressman, Pantaleo & Rinaudo (Calidad en el desarrollo de software), SWEBOK guide; standards ISO/IEC/IEEE 12207, ISO/IEC 25010:2023, ISO/IEC 33020, ISO/IEC/IEEE 14764, ISO 9001:2015, CMMI V3.0.
- **Tools/AI context named in the syllabus:** Jira/Trello/Azure DevOps, LMS/EVA, and AI tools for education, programming, document processing and UML generation.

**Coverage gap between syllabus and `servidor/documentacion/markdown/`:** measured in `servidor/reportes/cobertura_silabo.md` (regenerate with `pruebas/auditar_cobertura.py`): of 27 topics, 6 covered, 12 partial, 9 without coverage (Kanban, Lean, ISO/IEC 42001, KPIs/GQM, flow metrics, DORA, UX/security/sustainability metrics, TDD/automation, maintenance/ISO 14764). Questions on those hit the "insufficient context" path. The docs also include 20000, 27002, 29110, 31000 and 42010, which are not in the official syllabus (topic 2.8 keeps them in scope).

## Gotchas

- **Which Python runs the RAG:** the stack (langchain, chromadb, sentence-transformers, …) is installed in the system Python 3.14 (`C:\Python314`), not in `backend/venv`, which was created at another path (`...\OneDrive\Desktop\PROYECTO\backend\venv`) and only has FastAPI/uvicorn. `iniciar_servidor.bat` activates that venv, so it will fail at import until `pip install -r backend/requirements.txt` is run inside it (or the bat is changed to use the system Python). `requirements.txt` now lists the full stack.
- `base_vectorial/` is committed to git, so a rebuild shows up as binary changes. `servidor/documentacion_md/` (and `PROYECTO/documentacion_md/`) hold older copies of the standards and are not used; `servidor/backend/documentacion/` is empty.
- The small local LLM (`llama3.2`) can invent details even when the retrieved context is correct (e.g. it listed made-up clause names for ISO 9001 while the context had the real list) — this is prompt/model quality, not retrieval.
- `servidor/setup_backend.sh` is the original scaffolding script (generates a much simpler backend); the code has since diverged, so don't re-run it.
- `__pycache__/*.pyc` files and `backend/.env` are tracked in git, and there is no root `.gitignore`. Anything that opens `base_vectorial/` with Chroma (server, audit script) modifies its binaries: use a copy (see "Evaluation and coverage") and commit only the files you meant to.

## Reglas de trabajo autónomo

- Ejecuta cada tarea de principio a fin sin pedir confirmaciones intermedias.
- Al terminar cada tarea que funcione, haz commit automáticamente
  con mensaje descriptivo en español. No esperes a que yo lo pida.
- Nunca hagas push ni cambies de rama sin autorización explícita.
- Antes de dar por terminada una tarea, verifica que el servidor
  arranca sin errores.
- Al finalizar cada avance, actualiza BITACORA.md con: qué se
  implementó, qué archivos se tocaron, qué quedó pendiente y
  cuál es el siguiente paso.
- Si el contexto se está agotando, actualiza BITACORA.md antes
  de compactar.

## Reglas del producto (no negociables)

- La IA tutora nunca entrega la respuesta completa: orienta,
  da pistas y hace preguntas de reflexión.
- Responde únicamente con información recuperada por RAG de la
  carpeta documentacion. Si no está ahí, lo dice, no inventa.
- Solo un mensaje predefinido permitido: el saludo inicial.
- Prioriza soluciones gratuitas, locales y multiplataforma.