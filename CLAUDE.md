# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

"Guía Didáctica Interactiva de Realidad Aumentada con IA para Normativas de Ingeniería de Software" (Spanish-language project; docs, prompts and UI text are in Spanish). `PROYECTO/` holds two pieces that live in **two separate git repositories**:

| Folder | What | Git repository | Remote |
|---|---|---|---|
| `PROYECTO/` (root) → `servidor/` | FastAPI backend: a RAG "Tutor IA" that answers questions about ISO/IEC standards (9001, 12207, 20000, 25010, 27001, 27002, 29110, 31000, 33000, 42010) from Markdown documents, using a local Ollama LLM. Also `CLAUDE.md`, `BITACORA.md`. | root repo, branch `main` | `https://github.com/Sebastian-Paucar-R/guia-didactica-ra-ia.git` |
| `PROYECTO/app/` | **The current Flutter frontend** (login/register, 4 "worlds", chat, AR scanner, profile). | its own repo (nested, not a submodule), branch `main` | `https://github.com/V-Erik/normativas_app.git` (a teammate's repo) |

- The root `.gitignore` ignores `app/` so the two histories never mix: run git for the frontend from `app/` (or `git -C app ...`), for everything else from `PROYECTO/`. A change that spans both (e.g. a contract change) is **two commits, one per repo**.
- `_ARCHIVO_normativas_app_vieja/` is an **older, superseded copy** of the frontend (it used to be `normativas_app/` and was tracked in the root repo until 2026-10-06; it is git-ignored now and kept on disk only until someone confirms it can be deleted). Do not edit it or take it as a reference. The only things it had that `app/` lacks were a chat screen already wired to the Spanish `/api/v1/chat` contract (see "API contract (summary)" below), `withValues` instead of the deprecated `withOpacity` in 3 files, and the template test calling `NormativasApp`; none is a feature, all are trivial to redo.
- Other leftovers, not used: `PROYECTO/backend/app/core/config.py` (stray copy, tracked), `PROYECTO/documentacion_md/` and `servidor/documentacion_md/` (old copies of the standards).

The backend has a pytest suite (`servidor/backend/tests/`, run `python -m pytest` from `servidor/backend/`; it uses fake embeddings and temp dirs, so it never touches the real `documentacion/` or `base_vectorial/`). There is no linter config or CI. The frontend's real state is in "Frontend (`app/`)" below.

## Bitácora (`BITACORA.md`)

There is **one** bitácora for the whole project: `PROYECTO/BITACORA.md`, versioned in the **root repo** (`guia-didactica-ra-ia`), newest entry first — including entries about work done in `app/`. Reasons: it is a single chronological log of the project (a backend change and the app change that consumes it belong in the same entry); it lives next to this `CLAUDE.md`, which is also in the root repo; and `app/`'s remote belongs to a teammate, so our session log should not be pushed into their history. Rule: an entry about `app/` names the `app/` commit hash(es) it refers to, and the bitácora commit goes to the root repo. Do not create a second `BITACORA.md` inside `app/`; frontend reference docs (like `app/ESTADO_REAL.md`) do belong in `app/`.

## Running the backend

Windows-only workflow (paths are hard-coded, see below). External requirements: an [Ollama](https://ollama.com) server running locally with the `llama3.2` model pulled (`ollama pull llama3.2`); a Firebase project with Authentication enabled (`FIREBASE_CREDENTIALS_PATH` in `.env` — see README.md "Firebase Authentication"); the database migrated (`python scripts/inicializar_db.py`, from `servidor/backend/`, before the first run — see "Identity, database and generation queue" below).

```
servidor\iniciar_servidor.bat
```

This activates `backend\venv`, sets `PYTHONPATH=backend`, and runs from `servidor/`:

```
python -m uvicorn app.main:app --reload --port 8000 --app-dir backend
```

Paths (`documentacion/`, `base_vectorial/`) are resolved from the location of `app/core/config.py` (see `Settings`), not from the cwd, and can be overridden with the `DOCUMENTACION_DIR` / `BASE_VECTORIAL_DIR` env vars. `GET /` serves the HTML test page `app/static/index.html` (docs list + upload/indexing panel + chat + localStorage history — this page predates auth and does not send an `Authorization` header, so it can no longer call `/chat` against a server with real Firebase credentials configured); `POST /api/v1/chat` requires `Authorization: Bearer <id_token>` and an accepted consent (`POST /api/v1/usuarios/consentimiento`, else 409), takes `{mensaje, conversacion_id?, leccion_id?}` (no `user_id`: it comes from the verified token) and returns `{respuesta, tipo, conversacion_id, desde_cache, latencia_ms, tema_detectado, unidad_detectada, ..., posicion_en_cola, espera_estimada_s}` — full contract in `servidor/docs/contrato_api.md`; `GET /api/v1/salud` is the only unauthenticated endpoint (server/model/Ollama/index status, for the app to check before letting the student type); `GET /documentacion/{originales|pdf|markdown}/{archivo}` serves a copy of a document (the old `GET /documentacion/{archivo}` still works and looks in `pdf/`, `markdown/`, `originales/`). The document endpoints are described in "Document upload" below.

When running the server with stdout redirected on Windows (e.g. from a script), set `PYTHONUTF8=1`: `chat.py` prints a `→` that raises `UnicodeEncodeError` under cp1252 (a real console is fine).

Flutter app (from `app/`): `flutter pub get`, `flutter run`, `flutter analyze`, `flutter test`, `flutter build web`.

## Frontend (`app/`)

Full, file-by-file inventory with evidence: `app/ESTADO_REAL.md` (2026-10-06) — read it before working on the app. Summary:

- Since `app` commit `f11a36a` (2026-10-06): dead code removed, `withOpacity` → `withValues`, `avatar.glb` + `model_viewer_plus` removed, Firebase deps added; `flutter analyze` clean, `flutter test` 2/2, debug APK builds. `ESTADO_REAL.md` is the snapshot from *before* that commit.
- `lib/` = `main.dart` + `models/` (2) + `screens/` (8) + `theme/` + `widgets/` (8). No `services/`, no state management. Deps: `http`, `lottie`, `mobile_scanner`, `firebase_core`, `firebase_auth`, `google_sign_in`, `shared_preferences` (the last four added but **not wired yet**: no `firebase_options.dart` / `google-services.json` until `flutterfire configure` is run).
- Navigation: `MaterialApp(home: LoginScreen)` ⇄ `RegisterScreen` → `MainScaffold` (4 tabs: `HomeScreen`, `ChatScreen`, `ArScannerScreen`, `ProfileScreen`) → `IsoLevelScreen`.
- Everything is mock data: login/register are a `Future.delayed`; the 4 worlds are 4 norms (25010, 12207, 27001, 33001 — not the 4 syllabus units) with 17 levels that are only an icon + a hard-coded state, no lesson content and no lesson screen; user name, streak, XP and medals are literals. No progress is stored anywhere.
- **Chat does not match the backend**: `lib/screens/chat_screen.dart` POSTs `{message, normativa}` to `http://10.0.2.2:5000/api/chat` and reads `reply`/`response`, no `Authorization`, no `conversacion_id`, 20 s timeout. See the contract below for what it must send.
- AR = `mobile_scanner` QR reader + a remote 2D Lottie overlay. No 3D model is bundled (the old static `avatar.glb` was removed; recover from `app` commit `fb4a6dd` if needed, but optimize it first).
- Ids: Android `applicationId`/`namespace` and iOS/macOS bundle id = `ec.edu.upec.tutornormativas` (`MainActivity.kt` under `kotlin/ec/edu/upec/tutornormativas/`); Dart package name is still `normativas_app` (imports use `package:normativas_app/...`). `minSdk = flutter.minSdkVersion` (24 with Flutter 3.44.8; Firebase Auth needs ≥ 23), release signed with debug keys, `usesCleartextTraffic="true"`.
- Windows host gotcha: `flutter pub get` warns "Building with plugins requires symlink support" — enable Windows Developer Mode for Windows-desktop builds; analyze/test/APK work without it.
- Push: `Sebastian-Paucar-R` has no write access to `V-Erik/normativas_app` (403 on 2026-10-06); `app/` commits stay local until that is granted.

## API contract (summary)

Full contract: `servidor/docs/contrato_api.md` (source of truth, kept in sync with `chat.py`'s `ChatRequest`/`ChatResponse`); Postman: `servidor/docs/tutor_ia.postman_collection.json`. Field names are Spanish and exact.

- **Base URL** (dev): `http://127.0.0.1:8000`; Android emulator `http://10.0.2.2:8000`; physical device: the PC's LAN IP. All routes under `/api/v1`. Not 5000, not `/api/chat`.
- **Auth**: every route except `GET /salud` and `GET /cola/estado` needs `Authorization: Bearer <Firebase id_token>` (same Firebase project as the backend's `FIREBASE_CREDENTIALS_PATH`). The backend creates the user (role `estudiante`, consent false) the first time it sees a uid; never send a `user_id`/`uid` in a body. Errors: 401 missing/invalid token · 403 wrong role or someone else's data · 409 consent not accepted (chat only).
- **App start-up flow**: Firebase sign-in → `GET /salud` → `GET /usuarios/yo` → if `consentimiento_aceptado == false`, `POST /usuarios/consentimiento` (no body) → chat.

| Method & path | Request | Response (main fields) |
|---|---|---|
| `GET /salud` (public) | — | `{estado: "ok"\|"degradado", modelo, ollama_disponible, documentos_indexados, chunks_indexados}` |
| `GET /cola/estado` (public) | — | `{limite, generando, en_espera, tiempo_medio_generacion_s, espera_maxima_s}` |
| `GET /usuarios/yo` | — | `{uid, correo, nombre, foto_url, proveedor, rol: estudiante\|docente\|admin, fecha_registro, ultimo_acceso, consentimiento_aceptado, consentimiento_fecha}` |
| `POST /usuarios/consentimiento` | no body | same as `/usuarios/yo`, consent true |
| `POST /chat` | `{mensaje: str (required), conversacion_id?: str≤100, leccion_id?: str≤100}` | `{respuesta, tipo, conversacion_id, desde_cache, latencia_ms, tema_detectado, unidad_detectada, tema_id_detectado, metodo_deteccion, adaptacion, posicion_en_cola, espera_estimada_s, espera_real_s}` |
| `GET /progreso/mio` | — | `{xp_total, racha_actual, racha_mejor, ultima_actividad_fecha, lecciones_completadas, ejercicios_resueltos, ejercicios_correctos}` (zeros if no activity) |
| `POST /progreso/lecciones/{leccion_id}/completar` | no body | updated progress (same shape). +20 XP |
| `POST /progreso/ejercicios/{ejercicio_id}/resolver` | `{correcto: bool (required), leccion_id?: str}` | updated progress. +10 XP correct / +2 incorrect |
| `GET /historial/conversaciones` | — | `[{id, titulo, fecha_inicio, fecha_ultimo_mensaje}]` newest first |
| `GET /historial/conversaciones/{id}/mensajes` | — | `[{rol: estudiante\|tutor, contenido, tipo, fecha}]`; 404 if not yours |
| `GET /perfil/{uid}`, `GET /perfil/{uid}/progreso`, `POST /perfil/{uid}/reiniciar` | own uid only (403) | adaptive profile / level per unit over time (estimated by the tutor, not the app's XP) |

`/chat` details the client must handle:
- `conversacion_id`: omit it on the first message, store the one returned, resend it for the rest of the thread (that's the tutor's memory; it lives in server RAM).
- `leccion_id`: send it when the chat is opened from a lesson; must equal a key in `servidor/configuracion/lecciones.json` (e.g. `leccion-iso-9001`, `leccion-iso-25010`) to have an effect — unknown ids are ignored, not an error. Progress endpoints accept any `leccion_id`.
- `tipo` ∈ `saludo | funcionamiento | sin_documentos | respuesta | sin_contexto | redireccion | error`; `error` still comes with HTTP 200 (text in `respuesta`).
- `adaptacion` = `{nivel: bajo|medio|alto, profundidad: breve|media|extensa, estilo: conceptual|ejemplos|comparativo, dificultad: bool, segmento: str, referencias: [{tema_id, tema, unidad}]}` or null.
- `posicion_en_cola`/`espera_estimada_s`: show "waiting in line" when non-null. Errors: 422 (missing `mensaje`, ids > 100 chars), **503 when the queue wait passes 90 s** (retry later). A generation takes ~10–13 s, plus queue wait: client timeout must be ≥ 120 s.

## Backend architecture

Layers (all under `servidor/backend/app/`): HTTP layer (`main.py`, `api/v1/endpoints/*.py`, `api/deps.py`) →
service layer (`services/rag_service.py`, `services/conversion_service.py`, `services/cache_service.py`,
`services/perfil_service.py`, `services/adaptacion_service.py`, `services/historial_service.py`,
`services/cola_service.py`, `services/progreso_service.py`; data model in `models/perfil.py`) → Chroma vector
store + Ollama LLM, and →
`app/db/` (SQLAlchemy models + session factory) for identity/persistence. Two separate SQLite databases stay
outside `DATABASE_URL` on purpose: the semantic answer cache (see "Semantic cache") because it must be wiped on
every reindex, and `perfiles.db` no longer exists — profiles moved into the relational DB (see "Identity,
database and generation queue"). Conversation memory ALSO lives in RAM per `conversation_id`
(`services/memoria_service.py`, lost on server restart, used for fast follow-up reformulation) *in addition to*
the durable `conversaciones`/`mensajes` tables (`historial_service.py`) — two different concerns, kept apart
deliberately (see that section). The HTML test page also keeps its own chat history in browser `localStorage`
(`tutor_history`, plus `tutor_conversation_id`), but predates Firebase auth and can't call `/chat` for real once
`FIREBASE_CREDENTIALS_PATH` is configured.

- `app/main.py` — creates the FastAPI app, CORS (`allow_origins=["*"]`, `allow_credentials=False` — the invalid
  `"*"` + `allow_credentials=True` combo browsers reject was fixed; identity travels in `Authorization`, not
  cookies, so no request needs credentialed CORS), mounts all `/api/v1` routers (chat, documentos, cache, perfil,
  usuarios, historial, docente, progreso, salud), serves `static/index.html` at `/` and the `/documentacion/...`
  file routes; on startup, raises anyio's default threadpool limit (see "Identity, database and generation
  queue"). Settings come from `app/core/config.py`; `.env` is empty (see `.env.example` for the real keys —
  `DATABASE_URL`, `FIREBASE_CREDENTIALS_PATH`, etc.). A stray copy of `config.py` is tracked at
  `PROYECTO/backend/app/core/config.py`.
- `app/api/deps.py` — FastAPI dependencies for identity: `usuario_actual` (verifies the Firebase token, creates
  the `Usuario` row on first sight), `usuario_con_consentimiento` (+ 409 if consent isn't accepted),
  `requiere_rol(*roles)`, `verificar_propietario` (a student can only touch their own `/perfil/{uid}`).
- `app/api/v1/endpoints/chat.py` — the `/chat` endpoint; tries `RAGService.probar_cache` first (cache hits skip
  the queue entirely), then generates inside the generation queue (`services/cola_service.py`) via
  `RAGService.get_answer`, both through `get_rag_service()`. The HTTP contract is Spanish field names (see
  `servidor/docs/contrato_api.md`, written for the Flutter integration): request `{mensaje, conversacion_id?,
  leccion_id?}`, response `{respuesta, tipo, conversacion_id, desde_cache, latencia_ms, tema_detectado,
  unidad_detectada, tema_id_detectado, metodo_deteccion, adaptacion, posicion_en_cola, espera_estimada_s,
  espera_real_s}` — the internal `RAGService.get_answer` dict (`response`/`context`/`tiempo_respuesta_ms`/a
  dataclass-shaped `ubicacion`) is translated at this layer, not renamed internally; `context` (retrieved text,
  truncated to 1000 chars) and `fuentes` exist internally but are not exposed over HTTP. Also `GET /cola/estado`.
- `app/api/v1/endpoints/{usuarios,historial,docente}.py` — consent, own conversation history, teacher-only
  aggregate stats (see "Identity, database and generation queue").
- `app/api/v1/endpoints/progreso.py` — app gamification (XP, streak, lessons, exercises), `app/api/v1/endpoints/
  salud.py` — public health check (see "Identity, database and generation queue").
- `app/api/v1/endpoints/documentos.py` — upload / reindex (both `requiere_rol("docente", "admin")`) / list
  (public) endpoints.
- `app/services/rag_service.py` — all RAG logic (LangChain). `get_rag_service()` returns the one shared instance.
- `app/services/pertinencia_service.py` — relevance filter (tutor-question detection, role-change detection, classifier that picks a syllabus topic or FUERA, redirect generation); `app/core/silabo.py` — loads and validates `servidor/configuracion/silabo.yaml` (the single source of the syllabus: 4 units, 27 topics, each with `id`, `nombre`, `unidad`, `palabras_clave`, `archivos`), keyword matching (`buscar_por_palabras_clave`) and the texts inserted into prompts (+ `ubicar_en_silabo`: which unit covers a term). A broken YAML fails at server start (`RAGService.__init__` calls `cargar_silabo()`); path via `SILABO_PATH`.
- `app/services/tutor_service.py` — the tutor prompt and its helpers (student intent, follow-up rewriting, context formatting, checks on what the LLM wrote); `app/services/memoria_service.py` — per-conversation memory.
- `app/services/conversion_service.py` — PDF/Markdown conversion of uploaded files.

`RAGService` request flow for `get_answer(question, conversation_id=None, user_id=None, leccion_id=None)`
(returns `{response, context, tipo, fuentes, desde_cache, tiempo_respuesta_ms, ubicacion, adaptacion}`; `user_id`
is always the authenticated Firebase uid now — `POST /chat` no longer accepts it in the body, see "Identity,
database and generation queue"; `ubicacion` is always a plain dict (`.como_dict()`), never the `pertinencia.
Ubicacion` dataclass itself, by the time it leaves `_procesar`/`probar_cache`). `POST /chat` (Spanish contract,
`servidor/docs/contrato_api.md`) takes `{mensaje, conversacion_id?, leccion_id?}` and returns `{respuesta, tipo,
conversacion_id, desde_cache, latencia_ms, tema_detectado, unidad_detectada, tema_id_detectado, metodo_deteccion,
adaptacion, posicion_en_cola, espera_estimada_s, espera_real_s}` (`adaptacion` = `{nivel, profundidad, estilo,
dificultad, segmento, referencias}`, the profile adjustment the answer was generated with; null without `user_id`
and for answers that are not adapted) (`tema_detectado`/`unidad_detectada` come from `ubicacion.tema`/`.unidad`;
`tema_id_detectado`/`metodo_deteccion` are the same `ubicacion.tema_id`/`.metodo` exposed under extra names for
internal tooling — `pruebas/evaluar_tutor.py`, the pertinencia audit — that need the exact syllabus id and the
`palabras_clave | llm | embedding | leccion | seguimiento` method, not just the display name; all four are null
for redirects, greetings and questions about the tutor) (`posicion_en_cola`/`espera_estimada_s`/`espera_real_s`
come from the generation queue's `Espera`, see "Identity, database and generation queue"; all three null when the
request passed straight through or was served from cache) — if the client sends no id the server creates one and
returns it; the HTML page stores and resends it (the Flutter app doesn't yet — see "Frontend (`app/`)"); `tipo` is one of `saludo |
funcionamiento | sin_documentos | respuesta | sin_contexto | redireccion | error`):

1. **Greeting shortcut** — if the lowercased question is exactly one of a short list (`hola`, `buenas`, `buenos días`, `buenas tardes`, `hey`, `hi`, `hoola`) a fixed welcome message is returned with no retrieval or LLM call (`tipo: saludo`). This is the only canned reply.
2. **Questions about the tutor itself** (`pertinencia_service.es_pregunta_sobre_tutor`, regexes on 2nd-person phrasing: "¿qué puedes hacer?", "¿qué documentos tienes?", "¿de qué temas me puedes ayudar?"...) skip the filter and are answered by the LLM from real data (indexed document names + syllabus units) — `tipo: funcionamiento`.
3. **Guard** — if the collection has zero chunks it returns a "no documents loaded" message (`sin_documentos`).
4. **Memory** — the last turns of that `conversation_id` are loaded; if the message is a follow-up ("explícame eso mejor", refers to "eso", or is ≤3 words) `reformular_pregunta` rewrites it as a standalone question (only then: rewriting independent questions made the LLM paste history into them). Retrieval and the relevance filter use that standalone question.
5. **Lesson override** (`leccion_id`, app only — see "Identity, database and generation queue") — if it resolves to a syllabus topic (`core/lecciones.py:resolver_leccion`), retrieval is restricted to that topic's declared documents (Chroma `where nombre_archivo $in [...]`) and `ubicacion` is forced to that topic (`metodo: leccion`), skipping steps 6-7 below entirely — the lesson already says what the question is about. An unresolved `leccion_id` (empty, unknown) changes nothing. These answers skip the semantic cache in both directions (no lookup, no save): the context that generated them depends on the lesson, not just the question text.
6. **Retrieve with score** — top-4 chunks with cosine similarity (`buscar_con_score`), filtered to the lesson's documents when step 5 applies.
7. **Relevance filter** — see "Relevance filter" below. Skipped when step 5 already forced a topic. Off-topic → `tipo: redireccion`, no answer content. In-topic → the unit/topic is recorded (`[FILTRO] ... unidad=U tema=U.N metodo=...` in the log and `ubicacion` in the response). **Insistence** (`tutor.insistencia`): if the conversation's last turns were TAREA requests the tutor answered and the new message pushes again ("insisto", "sin pistas", "dame la tabla ya terminada, por favor"), the message skips the filter and the cache, retrieval uses the *original* task (`tutor.tarea_original`) and the prompt switches to `INSTRUCCIONES_TAREA_INSISTENTE` (firm, a new more concrete hint, never the solution).
8. **Intent** (`tutor_service.detectar_intencion`): explicit cues first (`resuélveme`, `hazlo por mí` → TAREA; `explícame mejor`, `no entendí`, `ejemplo`, `amplía` → PROFUNDIZAR), then a direct question ("qué es", "cuál es la diferencia", "cuándo aplica"...) → PUNTUAL without any LLM call, and only for imperatives/references a short LLM classification (the small LLM classified almost every conceptual question as PROFUNDIZAR, hence the rules). PROFUNDIZAR retrieves k=6 anchored on the previous student question.
9. **Missing terms** (`terminos_sin_respaldo`) — if the student names a norm number, acronym (CMMI, DORA, CI/CD), mixed-case term (DevOps) or syllabus proper name (Scrum, Kanban) that is not in the retrieved context or document names, the tutor does NOT explain it: `PROMPT_SIN_CONTEXTO` says it is not in the documents and points to the real syllabus unit (`ubicar_en_silabo`) → `tipo: sin_contexto`. A prompt-level warning was not enough with llama3.2.
10. **Generate** — `PROMPT_TUTOR` with the mode text for the intent and, with a `user_id`, the student-profile block `{adaptacion}` (empty for anonymous or brand-new students, so their prompt is byte-identical to the pre-profile one; see "Student profile") (PUNTUAL: ≤3 sentences + one short reflection question, appended by the LLM if missing; PROFUNDIZAR: several paragraphs + a software-development example; TAREA: numbered steps with hints, never the finished work) plus a one-line reminder of the mode right before the answer. Context fragments are labelled `[Documento: name — «title»]`. Guard rails on the output: preamble/greeting/apology stripped, pasted document labels replaced by the title, dangling "Referencias:" removed, cut-off sentence trimmed, unsupported ISO numbers/years/clauses/counts/acronyms trigger one retry (then those sentences are removed), a TAREA answer with <3 numbered steps or <45 words is retried (max 2). The LLM is `ChatOllama` with `num_ctx=8192`, `num_predict=1024`, `repeat_penalty=1.15`, temperature 0.35 (without the caps llama3.2 once produced 3,800 words in a loop). Any exception is caught and returned as the response text (HTTP status stays 200, `tipo: error`).

## Semantic cache (caché semántico de respuestas)

Before the flow above, `get_answer` looks the question up in `servidor/cache_respuestas.db` (SQLite, git-ignored via `servidor/.gitignore`; no in-memory copy, so it survives restarts). Code: `services/cache_service.py` (`CacheSemantico`), hooks in `rag_service.py`, stats endpoint `GET /api/v1/cache/estadisticas` (`{total_entradas, consultas, aciertos, fallos, tasa_aciertos, preguntas_mas_repetidas (top 10 by usos>0), tiempo_promedio_ahorrado_ms, tiempo_total_ahorrado_ms, umbral_similitud, invalidaciones, ultima_invalidacion, motivo_ultima_invalidacion, entradas_por_segmento, omitidos_por_perfil}`; 503 if `CACHE_ACTIVO=false`). Full method, calibration and measured results: `backend/documentacion/cache_semantico.md`.

- **Hit** = embedding (same MiniLM as the RAG) with cosine ≥ `CACHE_UMBRAL_SIMILITUD` (**0.95**, env-overridable; the requested 0.92 let through a real wrong hit, "qué es ISO 25010" → "cuáles son las características de ISO 25010" = 0.927) among entries with the same intent bucket (TAREA/PROFUNDIZAR by explicit cues, else PUNTUAL — no LLM), the same numbers/acronyms (ISO 9001 ≠ 27001) and the same negation. A hit calls no LLM and returns `desde_cache: true`; it also goes into the conversation memory. Miss → normal flow, then the answer is stored if `tipo ∈ {respuesta, sin_contexto}` (never saludo/funcionamiento/redireccion/sin_documentos/error).
- **Bypassed entirely**: greetings, questions about the tutor, and follow-ups inside a conversation (`es_seguimiento` with history: the answer depends on the history).
- **Per-student segmentation (decision, adaptive profile)**: a cached answer for a level-2 student must not be served to a level-5 one, so every entry carries a `segmento` (column added by `_migrar` to old DBs; old entries = `''`) and `buscar`/`guardar` take it. Chosen over "cache only the factual core and generate the pedagogical wrapper on each query" because the cache saves the LLM generation (measured ~10–13 s → 0.02 s); caching only the retrieved context would save tens of ms (<2 %), and caching a neutral answer to be rewritten per profile still needs one LLM call per query (most of the saving gone) and exposes the normative content to being distorted by a 3B model, which is exactly what the profile must never do.
  - `segmento` is a function of the directive actually injected in the prompt (`n=<bajo|alto>|p=<breve|extensa>|e=<ejemplos|comparativo>|d=1`, only non-neutral parts, order fixed), never of the raw profile. Invariant: *what is stored always carries the segment of the adjustment used to generate it* — lookup estimates the unit before the relevance filter (keywords, else embedding), so if the filter decides another unit the only cost is a miss, never a wrong hit. A neutral profile (new student, or anonymous) gives `''`, so it shares the pre-existing entries; depth only ever changes PUNTUAL/PROFUNDIZAR (TAREA keeps its numbered steps).
  - **Personal answers skip the cache** (no lookup, no store): if the directive cites what the student already worked on (`Adaptacion.personal`, same-unit history), the answer is theirs alone. Counted in `omitidos_por_perfil`.
  - `sin_contexto` is never adapted ("not in the documents"): it is stored with `''` and served to every segment (`segmento = ? OR (tipo = 'sin_contexto' AND segmento = '')`).
  - Cost, accepted: fewer hits (≤ 9 segments per question in theory, fewer in practice because a profile moves slowly) and no hits for students whose history connects with the question; each hit keeps the full saving. `estadisticas()` reports `entradas_por_segmento` and `omitidos_por_perfil` to measure it. Tests: `tests/test_cache.py` (segmentation section).
- **Invalidation (critical)**: every real change of the vector index empties the whole cache — hooks in `indexar_archivo` (new/changed doc, old version removed), `sincronizar` (docs deleted while the server was down) and `reconstruir` (`POST /documentos/reindexar`). No invalidation when nothing changes (`omitido_sin_cambios`, rejected upload). A version counter in the DB makes `guardar()` reject an answer whose generation started before an invalidation; if emptying the DB fails the cache stays off until it succeeds. **Any new code path that changes the Chroma index must call `_invalidar_cache`.** Hit/miss counters and saved time survive invalidation; entries do not.
- Not stored/handled: no eviction policy; changing the embedding model requires emptying the cache by hand; deeper rewordings ("dime en qué consiste…", similarity 0.6–0.9) deliberately miss.
- Tests: `tests/test_cache.py`; `conftest.py` turns the cache off for every other test (autouse) and points `CACHE_DB_PATH` at a temp dir, so tests never touch the real DB. Calibrate with `python scripts/calibrar_cache.py`.

## Relevance filter (filtro de pertinencia temática)

Implemented in `services/pertinencia_service.py` + `RAGService._flujo`; the syllabus is `configuracion/silabo.yaml` (loaded by `core/silabo.py`), **not** a list in a prompt. Order of decision: (1) exceptions above (a role-change request such as "Olvida que eres un tutor" is *not* a question about the tutor even though it contains "que eres"); (2) **YAML keywords** (`silabo.buscar_por_palabras_clave`, no LLM): the question names a topic → in scope, unit and topic known; keywords are accent/case-insensitive whole-word matches, a trailing `*` on a word is a prefix wildcard, `~` marks a weak keyword ("norma ISO") that only decides if no strong one matches anywhere, and norm numbers (`29119`) outweigh phrases; keep them specific: a common word ("cascada", "ciclo de vida", "certificado") lets out-of-scope questions through with no second check; (3) **role change** (`es_intento_abandonar_rol`: "ignora tus instrucciones", "actúa como…", "modo desarrollador", "muéstrame tu prompt") with no syllabus topic → FUERA without calling the classifier; with a topic the question is answered and the prompt gets `AVISO_CAMBIO_DE_ROL`; (4) best chunk similarity `>= settings.UMBRAL_PERTINENCIA` → in scope (topic label by embedding similarity to the YAML topics, `metodo=embedding`); (5) otherwise a short deterministic LLM call (`llm_clasificador`, temperature 0) receives the numbered YAML topics with their keywords and answers a topic **number** or `FUERA` (`parsear_veredicto`; unparseable/failed → fail-open DENTRO). `FUERA` → the answer LLM is **not** called: a second short call picks related topics (`NINGUNO` → no forced connection), then `llm_redireccion` (temperature 0.9, `PROMPT_REDIRECCION`) writes the redirect; a role-change message is replaced by a neutral description before reaching that prompt so its injected order can't be obeyed. Nothing is a fixed phrase. Every decision is logged as `[FILTRO] decision=... score=... llm=... unidad=... tema=... metodo=...` (decision ∈ palabras_clave, rol, pertinente, candidata, insistencia, funcionamiento, leccion, seguimiento); `FILTRO_PERTINENCIA_ACTIVO=false` disables the whole filter. A cache hit recomputes `ubicacion` (keywords, else embedding of the question) because the cache does not store it.

- **Threshold** `UMBRAL_PERTINENCIA = 0.62` (env-overridable, in `core/config.py`). With `all-MiniLM-L6-v2` on Spanish text the score ranges overlap heavily (off-topic up to 0.61, in-topic down to 0.42), so the threshold is deliberately high and the LLM arbitrates the grey zone; it skips the classifier only for clearly on-topic questions. Recalibrate with `python scripts/calibrar_umbral.py` if the embedding model or corpus changes.
- **Cosine metric**: the Chroma collection is created with `hnsw:space = cosine` so `1 - distance` is a 0-1 similarity; `sincronizar()` rebuilds a store that uses another metric (once).
- Evaluation: `pruebas/evaluar_tutor.py` (60-question bank, see next section) and the older `scripts/evaluar_pertinencia.py` (questions in `scripts/preguntas_pertinencia.py`, useful as an independent regression set). Method: `backend/documentacion/filtro_pertinencia.md`.
- `llama3.2` (3B) is weak at this: prompts were tuned iteratively (separate topic-selection step; the rule "do not answer the question" goes first in the redirect prompt; the classifier prompt warns that sharing a word with the syllabus, "integración por partes" vs. "pruebas de integración", does not put a question in scope). A two-step classifier (DENTRO/FUERA first, number after) was tried and rejected: it fixed that case but wrongly redirected 3 legitimate questions. If you change a prompt, the YAML or the model, rerun `pruebas/evaluar_tutor.py` (see "Evaluation and coverage") and `scripts/evaluar_pertinencia.py`.

Ingestion is incremental and only reads `documentacion/markdown/*.md` (see "Document upload" below): split with `RecursiveCharacterTextSplitter` (chunk 1000, overlap 200); embed with HuggingFace `sentence-transformers/all-MiniLM-L6-v2`; persist to Chroma (collection `langchain`). Chunks carry `nombre_archivo`, `hash`, `fecha_indexado`, `source`, `chunk`; the API still doesn't report which standard a chunk came from.

## Student profile (perfilado adaptativo)

`user_id` in `POST /chat` is optional; without it none of this happens and the tutor answers exactly as before. Code: `models/perfil.py` (`PerfilEstudiante`), `services/perfil_service.py` (SQLAlchemy, table `perfiles` in `DATABASE_URL` — see "Identity, database and generation queue"; off with `PERFIL_ACTIVO=false`; a separate table from the semantic-cache SQLite file because the cache is emptied on every index change and profiles must not be), `services/adaptacion_service.py` (signals, update rules, prompt directive), `api/v1/endpoints/perfil.py`. Tests never touch the real database (`conftest.py` points `DATABASE_URL` at a per-test temp SQLite file).

- **Model** (per `user_id`): `nivel_por_unidad` (float 1–5 for each of the 4 syllabus units, starts at 3; franjas: bajo < 2.5, medio, alto > 3.5), `temas_consultados` (YAML topic id → count), `temas_con_dificultad`, `profundidad_preferida` (breve | media | extensa), `estilo_preferido` (conceptual | ejemplos | comparativo), `ritmo` (a session is a `conversation_id`: messages per session and mean duration of sessions with ≥ 2 messages, now computed from `conversaciones`/`mensajes` — see "Identity, database and generation queue" — not stored on the profile itself), `historial_resumido` (last 5 distinct topics), plus the inference state `aclaraciones_por_tema` and `senales_recientes` (window of 12). Tables: `perfiles` (the model above, as JSON), `eventos_perfil` (every level change: unit, level, reason, topic, date).
- **Updates** (`RAGService._actualizar_perfil` after each turn, inside try/except: a profile failure never blocks an answer). Only observable behavior, never declarations, and gradual: "no entendí"/"sigo sin entender" → level −0.4 in that unit and the topic becomes a difficulty; "explícame mejor"/"otra vez"/"repite"/"aclara" → −0.4, difficulty from the 2nd time on the same topic; a candidate answer to the tutor's reflection question (previous tutor turn ended in `?`, the message is a ≥ 8-word statement that shares ≥ 2 content terms with it) confirmed CORRECTA by a short deterministic judge (`llm_clasificador`; conservative: doubt or failure = no change) → +0.3 on the previous topic's unit and clears its difficulty; ≥ 3 requests of one kind in the window change the style (`ejemplos`, `comparativo`; must beat the current style, a tie decides nothing) or move the depth **one step** (breve ↔ media ↔ extensa; opposite requests cancel), and the signals used are consumed so the next step needs fresh evidence. At most one level move per turn. Only answered turns (`respuesta`/`sin_contexto`) apply signals; a redirect, greeting or error only counts for `ritmo` ("explícame otra vez la relatividad" is not confusion about the last topic). A follow-up (history + `es_seguimiento`) stays on the previous topic unless it names another one by YAML keywords: the filter's LLM/embedding guess for a message with no topic of its own once filed "Muéstrame un ejemplo con un equipo pequeño" under maintenance (Unit 4) in a real run.
- **Prompt** (`adaptacion_service.construir_adaptacion` → `Adaptacion(texto, segmento, personal, ...)`; `{adaptacion}` sits right after `{modo}`). It modulates exactly three things: depth (PUNTUAL/PROFUNDIZAR length through `tutor.instrucciones_modo/recordatorio(intencion, profundidad)`; TAREA never changes: its numbered steps are a tutor rule), scaffolding (low level or a topic in `temas_con_dificultad` → everyday analogy first, short sentences, simple closing question; high level → straight to the concept and a demanding Socratic question, `terminar_con_pregunta(..., exigencia)`) and references to what was already worked on (≤ 2 topics of the *same unit*, one sentence; their YAML names are added to the `respaldo` of the citation checks). Every directive says that only HOW changes, never WHAT the norm says, and that analogies/contrasts must not carry facts that are not in the CONTEXT. **Invariants**: the role, robustness and no-invention rules and every output check (`normas_no_respaldadas`, `terminos_sin_respaldo`, TAREA steps, cleanups) apply unchanged to adapted answers; `PROMPT_SIN_CONTEXTO`, redirects and "about the tutor" are not adapted; a neutral profile yields a byte-identical prompt. `tests/test_adaptacion.py` asks the same question as three different students and checks the prompts differ only in `modo`, `recordatorio` and `adaptacion`.
- **Cache**: segmented by the adjustment, personal answers bypass it (decision and reasoning in "Semantic cache").
- **Endpoints** (`/api/v1/perfil`, 503 if `PERFIL_ACTIVO=false`): `GET /{uid}` (profile + `es_nuevo`, `resumen_historial`, `dificultades` with names; an unknown student gets the initial profile without creating it), `GET /{uid}/progreso` (per unit: title, `nivel_actual`, points `{fecha, nivel, motivo, tema_id}` starting from an `inicial` point at 3.0), `POST /{uid}/reiniciar` (deletes profile + `eventos_perfil`, keeps conversation history). `uid` is the Firebase uid; a student can only touch their own (`verificar_propietario`, 403 otherwise), docente/admin can touch any — see "Identity, database and generation queue".
- **Evaluation**: `pruebas/casos_adaptacion.json` + `pruebas/evaluar_adaptacion.py` → `reportes/evaluacion_adaptacion.{json,md}`: a novice, a new student and an advanced student ask the same three questions, then repeat them to check the cache by segment, and one real student is driven through the API (says "no entendí", asks for examples) to watch the profile move. Since `POST /chat` requires auth now, this script authenticates via a dependency override on `usuario_actual` in-process rather than a real Firebase token (see `backend/scripts/prueba_concurrencia.py` for the same pattern) — check it still matches before rerunning against a server started normally. **Read the answers, not the verdicts**: the automatic verdicts are heuristics (as of the last real run, `identificadores_coinciden` — same norm citations across the three profiles — was added and is stricter than before, by design: it now fails a case rather than call it a pass on a cosmetic mismatch). `reportes/evaluacion_adaptacion_lectura.md` (hand-written) holds the critical reading of an earlier run before the per-sentence attribution fix below.
- **Known limits, and what's already fixed**: earlier runs with a 3B model showed the normative content was NOT reliably the same for every profile (extended profile padding, attributes mixed between norms). Since then: (1) `tutor_service.atribuciones_no_respaldadas` checks, per sentence, that a cited norm has its own retrieved fragment and (for single-norm sentences) that its clause/count numbers come from THAT norm's fragment, not the pooled context — the concrete gap `normas_no_respaldadas` had; (2) `tutor.nivel_de_contexto` caps profundidad/PROFUNDIZAR by how much was actually retrieved, deterministically, regardless of what the profile prefers; (3) `terminos_sin_respaldo`/`atribuciones_no_respaldadas` use word-boundary matching (`_palabra_en`), not substring — "Dame" no longer matches inside "fundamentos"; (4) a pure follow-up with no topic of its own inherits the previous turn's topic directly (`Turno.ubicacion`) instead of risking the filter misjudging a reformulation. See `reportes/comparativa_modelos.md` for a real before/after and why `llama3.2` stays the default model. Still open: the reflection judge is weak with a 3B model (hence conservative and small); style/depth inference never goes back to `conceptual`/`media` by itself (use `/reiniciar`); the Flutter app doesn't send `Authorization`/consent yet, so it can't use any protected endpoint (see "Identity, database and generation queue").

## Identity, database and generation queue

Everything in this section was added to prepare the backend for the Flutter app (`app/`; when this was written
the app's repo wasn't known, so the contract below comes from the literal integration request, documented in full
in `servidor/docs/contrato_api.md` and summarized in "API contract (summary)" above).

- **Firebase Authentication** (`core/firebase_auth.py`, `api/deps.py`) is identity only — no password is ever
  stored in this project. Every endpoint except `GET /api/v1/salud` and `GET /api/v1/cola/estado` requires
  `Authorization: Bearer <id_token>`;
  `usuario_actual` verifies it (`firebase_auth.verificar_token`, swappable in tests via `app.dependency_overrides`
  with no real credentials needed — see `tests/test_auth.py`) and creates the `Usuario` row (role `estudiante`,
  `consentimiento_aceptado=False`) the first time a `uid` is seen; `usuario_con_consentimiento` additionally
  requires `POST /usuarios/consentimiento` to have been called first (409 otherwise); `requiere_rol(*roles)` gates
  `docente`/`admin`-only endpoints; `verificar_propietario` lets a student only touch their own `/perfil/{uid}`
  and `/historial/...` is scoped to the token's own uid, so it needs no such check. `user_id` is never a free body
  field anywhere — it always comes from the verified token.
- **Relational database** (`app/db/`: `base.py`, `models.py`, `session.py`; migrations in `backend/alembic/`,
  run with `python scripts/inicializar_db.py` before the first start). `DATABASE_URL` picks the engine: SQLite in
  a file by default (`servidor/tutor.db`, dev-friendly, zero setup), or `postgresql+pg8000://user:pass@host/db`
  for a real deployment. The driver is `pg8000` (pure Python), not `psycopg2`: this machine's Windows
  Application Control policy blocks `psycopg2`'s native binary, the same class of problem `core/chroma_compat.py`
  already works around for `grpc`/chromadb — `pg8000` sidesteps it by having no compiled extension at all.
  SQLite gets `PRAGMA foreign_keys=ON` per connection (a SQLAlchemy `connect` event listener in `session.py`), so
  an orphaned profile or conversation fails in dev exactly like it would in PostgreSQL. Seven tables: `usuarios`,
  `perfiles` (the adaptive profile, as JSON — see "Student profile"), `conversaciones`/`mensajes` (durable chat
  history, independent of the in-RAM `memoria_service.py` — see "Backend architecture"), `eventos_perfil` (every
  level change), `progreso_estudiante`/`eventos_progreso` (app gamification, below). Tests never touch the real
  database: `conftest.py`'s autouse fixture points `DATABASE_URL` at a fresh temp SQLite file per test and runs
  `Base.metadata.create_all` (not Alembic — that's only exercised for the real migration path).
- **Generation queue** (`services/cola_service.py`, `ColaGeneracion`, instantiated once at module level in
  `chat.py`) exists because one local Ollama model does not get faster with concurrent requests — it gets slower
  for all of them (`reportes/comparativa_modelos.md` already showed this class of degradation with larger
  models). `LIMITE_GENERACIONES_SIMULTANEAS` (2 by default) requests may generate at once; the rest wait their
  turn. Four deliberate design points (full reasoning in the module docstring):
  1. **`asyncio.Semaphore`, not `threading.Semaphore`.** Starlette's threadpool for sync code
     (`run_in_threadpool` → `anyio.to_thread.run_sync`) defaults to 40 threads
     (`anyio.to_thread.current_default_thread_limiter().total_tokens`, raised at startup in `main.py` anyway as
     extra margin). If waiting students blocked threadpool workers, 40 of them would stop the server from
     answering *anything*, even requests that never touch the model. So waiting (`cola.turno()`) is a coroutine
     awaited on the event loop — it holds no thread — and only the actual generation, once a slot is won, is
     dispatched to a thread (`run_in_threadpool(rag_service.get_answer, ...)`).
  2. **Cache hits never enter the queue.** They answer in ~20 ms with no LLM call
     (`RAGService.probar_cache`); `chat.py`'s `_generar_en_cola` tries it first and only calls `cola.turno()` on
     a miss — queuing a cache hit would turn its whole advantage into a wait.
  3. **The short calls inside one turn (relevance classification, follow-up reformulation, redirect wording) do
     share the queue slot with generation**, deliberately — they compete for the same Ollama/GPU resource as
     generation, and running them outside the queue would just move the saturation it exists to prevent, not
     remove it (they're also mandatory and prior: there is no generating without classifying first).
  4. **A hard wait cap with a real-data estimate.** `cola.turno()` uses `asyncio.wait_for(...,
     timeout=ESPERA_MAXIMA_COLA_S)` (90 s by default): past that, `TiempoDeEsperaAgotado` → `POST /chat` responds
     503 with a clear message instead of hanging the connection. The wait estimate shown to an arriving request
     is `posición × media móvil de las últimas generaciones reales` (`deque`, window of 20), not a constant, so
     it self-adjusts if the model, prompt length or machine changes.

  `GET /api/v1/cola/estado` gives a live snapshot (`{limite, generando, en_espera, tiempo_medio_generacion_s,
  espera_maxima_s}`) for polling between chat requests. A real load test
  (`backend/scripts/prueba_concurrencia.py`, in-process via `httpx.ASGITransport` with `usuario_actual`
  overridden — no real Firebase token needed — against the real RAG and `llama3.2`) is in
  `reportes/prueba_concurrencia.md`: 10/20/40 simultaneous requests, 0 errors, 0 timeouts, with the 40-request
  level's worst observed wait (72.6 s) already close to the 90 s cap — a margin to watch if real concurrency
  grows. The script's own first run hit `RuntimeError: ... bound to a different event loop` (calling
  `asyncio.run()` once per level while the queue's `asyncio.Semaphore`/`Lock` are module-level singletons bound
  to the first loop that touches them) — a bug in the *script*, not the server (a real uvicorn process has one
  event loop for its whole life); fixed by wrapping all levels in a single outer `asyncio.run()`.
- **Lesson-scoped retrieval** (`leccion_id` on `POST /chat`, app-only — see "Backend architecture" for how it
  changes `_flujo`): `core/lecciones.py` maps an app lesson id to a syllabus topic via
  `configuracion/lecciones.json` (editable, not versioned against `silabo.yaml` at the schema level). Unlike
  `core/silabo.py` (fails server startup on a bad YAML — the syllabus is load-bearing for the whole filter), a
  `lecciones.json` entry pointing at a topic id that no longer exists is just skipped with a printed warning:
  a lesson failing to resolve must never take the server down, since the tutor works fine without it (falls back
  to the normal relevance filter).
- **App progress (gamification)** (`services/progreso_service.py`, tables `progreso_estudiante`/
  `eventos_progreso`): XP, a daily streak (`racha_actual`/`racha_mejor`, one increment per calendar day with
  activity, reset after a gap of more than one day), lessons completed and exercises resolved/correct. This is
  explicit, student-declared activity in the app (a lesson marked done, an exercise answered) — a different
  thing from the adaptive profile's *estimated* level inferred from chat behavior (`models/perfil.py`); the two
  are stored separately and never mixed. Before this, the app kept XP/streak only in memory (lost on close).
  Endpoints (`api/v1/endpoints/progreso.py`, always the authenticated student's own — no uid is ever taken from
  the client, so there is nothing to own-check): `GET /progreso/mio`, `POST
  /progreso/lecciones/{leccion_id}/completar`, `POST /progreso/ejercicios/{ejercicio_id}/resolver`. Aggregated
  (never per-student) into `GET /docente/estadisticas` as `progreso_app`.
- **`GET /api/v1/salud`** (`api/v1/endpoints/salud.py`) needs no authentication (like `GET /cola/estado`): the
  app polls it to show whether the backend is reachable before letting the student type. It checks Ollama with a short
  (2 s) request to `OLLAMA_BASE_URL/api/tags` (`OLLAMA_BASE_URL` in `core/config.py`, also now passed explicitly
  to every `ChatOllama` instance in `rag_service.py` instead of relying on its default) and reports
  `{estado: ok|degradado, modelo, ollama_disponible, documentos_indexados, chunks_indexados}` — `degradado` means
  the process is up but Ollama isn't answering, not that the server itself is down.
- **CORS** (`main.py`): `allow_origins=["*"]`, `allow_credentials=False`. The previous `allow_credentials=True`
  alongside a wildcard origin is a combination browsers reject outright; it's unneeded here anyway since identity
  travels in the `Authorization` header, never a cookie, so no request depends on credentialed CORS.
- **API contract and client tooling**: `servidor/docs/contrato_api.md` is the full HTTP contract (every endpoint,
  request/response JSON, field meanings, error codes) — written to hand to whoever integrates the Flutter client;
  `servidor/docs/tutor_ia.postman_collection.json` is a matching Postman v2.1 collection (collection-level bearer
  auth via an `id_token` variable, `/salud` overridden to `noauth`). Keep both in sync with `chat.py`'s
  `ChatRequest`/`ChatResponse` if the contract changes again.
- **Known gap**: the current app (`app/lib/screens/chat_screen.dart`) still uses the old contract (`message` to
  `:5000/api/chat`, see "Frontend (`app/`)"), sends no `Authorization` and has no consent flow, so it cannot call
  this backend at all yet (the 2026-09-30 field-name fix went into the old copy, now archived). Evaluation scripts that hit
  `/chat` over real HTTP without a token (`pruebas/evaluar_tutor.py`, `backend/scripts/bateria_tutor.py`,
  `backend/scripts/evaluar_pertinencia.py`) have the same pre-existing gap — only `prueba_concurrencia.py` and
  `pruebas/evaluar_adaptacion.py` work around it with an in-process dependency override.

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
- Adaptation to the student (profile, see "Student profile") only changes HOW something is explained; these rules and the answer's normative content are the same for everyone.
- Not implemented (do not assume): quizzes or graded progress (the profile keeps an *estimated* level per unit inferred from behavior, not a grade), persistence of conversations across server restarts (the semantic cache persists answers and the profile persists the student, not conversations).

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
- Only `servidor/backend/.env.example` is tracked (not `.env`, not `__pycache__`); the root `.gitignore` only ignores `app/` and `_ARCHIVO_normativas_app_vieja/` (`servidor/.gitignore` covers the DBs). Anything that opens `base_vectorial/` with Chroma (server, audit script) modifies its binaries: use a copy (see "Evaluation and coverage") and commit only the files you meant to.
- `servidor/perfiles.db` (student profiles) is git-ignored like the cache DB. Running the real server without `PERFIL_DB_PATH` writes profiles there; evaluations should point both `CACHE_DB_PATH` and `PERFIL_DB_PATH` at new files.

## Reglas de trabajo autónomo

- Ejecuta cada tarea de principio a fin sin pedir confirmaciones intermedias.
- Al terminar cada tarea que funcione, haz commit automáticamente
  con mensaje descriptivo en español. No esperes a que yo lo pida.
- Nunca hagas push ni cambies de rama sin autorización explícita.
- Antes de dar por terminada una tarea, verifica que el servidor
  arranca sin errores.
- Commits en el repositorio que corresponda: `app/` tiene su propio repo
  (ver "Project"); nunca mezclar cambios de ambos en un commit.
- Al finalizar cada avance, actualiza `PROYECTO/BITACORA.md` (repo raíz,
  ver "Bitácora", también para trabajo en `app/`) con: qué se
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