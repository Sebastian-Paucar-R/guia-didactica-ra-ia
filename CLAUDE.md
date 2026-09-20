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

Layers (all under `servidor/backend/app/`): HTTP layer (`main.py`, `api/v1/endpoints/chat.py`, `api/v1/endpoints/documentos.py`) → service layer (`services/rag_service.py`, `services/conversion_service.py`) → Chroma vector store + Ollama LLM. There is no database, auth, or session state server-side: the HTML test page keeps chat history in browser `localStorage` (`tutor_history`), and `user_id` in `ChatRequest` is accepted but unused.

- `app/main.py` — creates the FastAPI app, CORS `*`, mounts the chat and documentos routers under `/api/v1`, serves `static/index.html` at `/` and the `/documentacion/...` file routes. Settings come from `app/core/config.py` (paths, allowed extensions, `MAX_UPLOAD_MB`); `.env` is empty. A stray copy of `config.py` is tracked at `PROYECTO/backend/app/core/config.py`.
- `app/api/v1/endpoints/chat.py` — the `/chat` endpoint; delegates everything to `RAGService.get_answer` via `get_rag_service()`. `context` in the response is the retrieved text truncated to 1000 chars.
- `app/api/v1/endpoints/documentos.py` — upload / reindex / list endpoints.
- `app/services/rag_service.py` — all RAG logic (LangChain). `get_rag_service()` returns the one shared instance.
- `app/services/pertinencia_service.py` — relevance filter (tutor-question detection, DENTRO/FUERA classifier, redirect generation); `app/core/silabo.py` — syllabus units.
- `app/services/conversion_service.py` — PDF/Markdown conversion of uploaded files.

`RAGService` request flow for `get_answer(question)` (returns `{response, context, tipo}`; `/chat` exposes `tipo`, one of `saludo | funcionamiento | sin_documentos | respuesta | redireccion | error`):

1. **Greeting shortcut** — if the lowercased question is exactly one of a short list (`hola`, `buenas`, `buenos días`, `buenas tardes`, `hey`, `hi`, `hoola`) a fixed welcome message is returned with no retrieval or LLM call (`tipo: saludo`). This is the only canned reply.
2. **Questions about the tutor itself** (`pertinencia_service.es_pregunta_sobre_tutor`, regexes on 2nd-person phrasing: "¿qué puedes hacer?", "¿qué documentos tienes?", "¿de qué temas me puedes ayudar?"...) skip the filter and are answered by the LLM from real data (indexed document names + syllabus units) — `tipo: funcionamiento`.
3. **Guard** — if the collection has zero chunks it returns a "no documents loaded" message (`sin_documentos`).
4. **Retrieve with score** — top-4 chunks with cosine similarity (`buscar_con_score`).
5. **Relevance filter** — see "Relevance filter" below. Off-topic → `tipo: redireccion`, no answer content.
6. **Generate** — `ChatPromptTemplate | ChatOllama(model="llama3.2", temperature=0.4) | StrOutputParser` (`respuesta`). Any exception is caught and returned as the response text (HTTP status stays 200, `status: "success"`, `tipo: error`).

## Relevance filter (filtro de pertinencia temática)

Implemented in `services/pertinencia_service.py` + `RAGService.get_answer`; syllabus units in `core/silabo.py` (`UNIDADES_SILABO`, source of truth for the classifier and redirects). Order of decision: (1) exceptions above; (2) best chunk similarity `>= settings.UMBRAL_PERTINENCIA` → answer normally, no extra LLM call; (3) otherwise the question is a *candidate* and a short deterministic LLM call (`llm_clasificador`, temperature 0) answers `DENTRO`/`FUERA` given the syllabus units. `DENTRO` (or an unparseable/failed classification — fail-open) → normal RAG answer, which says honestly when the documents lack the topic (many syllabus topics — Scrum, DORA, testing — have no document). `FUERA` → the answer LLM is **not** called: a second short call picks the syllabus topics that really relate to the question (`NINGUNO` → no forced connection), then `llm_redireccion` (temperature 0.9, prompt `PROMPT_REDIRECCION`) writes the redirect. Nothing is a fixed phrase. Every decision is logged as `[FILTRO] decision=... score=... llm=...` (use it to count redirects); `FILTRO_PERTINENCIA_ACTIVO=false` disables the whole filter.

- **Threshold** `UMBRAL_PERTINENCIA = 0.62` (env-overridable, in `core/config.py`). With `all-MiniLM-L6-v2` on Spanish text the score ranges overlap heavily (off-topic up to 0.61, in-topic down to 0.42), so the threshold is deliberately high and the LLM arbitrates the grey zone; it skips the classifier only for clearly on-topic questions. Recalibrate with `python scripts/calibrar_umbral.py` if the embedding model or corpus changes.
- **Cosine metric**: the Chroma collection is created with `hnsw:space = cosine` so `1 - distance` is a 0-1 similarity; `sincronizar()` rebuilds a store that uses another metric (once).
- Evaluation: `scripts/evaluar_pertinencia.py` (end to end against a running server; questions in `scripts/preguntas_pertinencia.py`). Results and method: `backend/documentacion/filtro_pertinencia.md`.
- `llama3.2` (3B) is weak at this: prompts were tuned iteratively (inclusive classifier rule "if in doubt, DENTRO"; separate topic-selection step; the rule "do not answer the question" goes first in the redirect prompt). If you change a prompt or model, rerun `evaluar_pertinencia.py`.

Ingestion is incremental and only reads `documentacion/markdown/*.md` (see "Document upload" below): split with `RecursiveCharacterTextSplitter` (chunk 1000, overlap 200); embed with HuggingFace `sentence-transformers/all-MiniLM-L6-v2`; persist to Chroma (collection `langchain`). Chunks carry `nombre_archivo`, `hash`, `fecha_indexado`, `source`, `chunk`; the API still doesn't report which standard a chunk came from.

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

These are the rules currently encoded in the prompt in `rag_service.py` (Spanish, university-tutor persona for ISO 9001, 25010, 27001, 12207, etc.). Keep any prompt change consistent with them:

- Answer only from the retrieved context; if the context is insufficient, say so honestly instead of filling in from the model's own knowledge. When retrieval returns nothing the prompt is fed the literal "No se encontró información relevante en los documentos."
- Off-topic questions (outside the syllabus) are redirected, never answered — see "Relevance filter".
- Natural, conversational Spanish; adapt depth to the student's question.
- May explain, give examples, ask reflection questions, or go deeper as needed — but must **not** follow a fixed script or predefined sequence of steps (the code deliberately has no lesson flow or state machine; only the greeting shortcut is canned).
- Not implemented (do not assume): quizzes, progress tracking, per-user memory across turns (each `/chat` call is stateless — the LLM sees only the current question and retrieved context), citation of sources.

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

**Coverage gap between syllabus and `servidor/documentacion/markdown/`:** the indexed docs cover ISO 9001, 12207, 25010, 27001, 33000 (SPICE), but the syllabus also requires ISO/IEC/IEEE 29119 (testing), ISO/IEC 14764 (maintenance), ISO/IEC 42001 (AI), and CMMI, and the metrics/agile/DevOps units have no source documents at all — questions on them will hit the "insufficient context" path. Conversely, the docs include 20000, 27002, 29110, 31000 and 42010, which are not in the syllabus.

## Gotchas

- **Which Python runs the RAG:** the stack (langchain, chromadb, sentence-transformers, …) is installed in the system Python 3.14 (`C:\Python314`), not in `backend/venv`, which was created at another path (`...\OneDrive\Desktop\PROYECTO\backend\venv`) and only has FastAPI/uvicorn. `iniciar_servidor.bat` activates that venv, so it will fail at import until `pip install -r backend/requirements.txt` is run inside it (or the bat is changed to use the system Python). `requirements.txt` now lists the full stack.
- `base_vectorial/` is committed to git, so a rebuild shows up as binary changes. `servidor/documentacion_md/` (and `PROYECTO/documentacion_md/`) hold older copies of the standards and are not used; `servidor/backend/documentacion/` is empty.
- The small local LLM (`llama3.2`) can invent details even when the retrieved context is correct (e.g. it listed made-up clause names for ISO 9001 while the context had the real list) — this is prompt/model quality, not retrieval.
- `servidor/setup_backend.sh` is the original scaffolding script (generates a much simpler backend); the code has since diverged, so don't re-run it.
- `__pycache__/*.pyc` files and `backend/.env` are tracked in git, and there is no root `.gitignore`.

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