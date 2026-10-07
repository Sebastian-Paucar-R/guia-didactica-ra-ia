# BITÁCORA

## 2026-10-06 — Orden de repositorios: copia vieja del frontend archivada, CLAUDE.md con la estructura real

### Qué se hizo
- Comparadas `normativas_app/` y `app/`: la copia vieja no tiene ninguna funcionalidad que falte en `app/`
  (solo `stat_chip.dart`, de un diseño de inicio ya reemplazado). Sí tenía 3 arreglos triviales que `app/` no:
  el chat ya cableado al contrato en español de `/api/v1/chat` (`mensaje`, `conversacion_id`, `respuesta`,
  `127.0.0.1:8000`; hecho en `afcc6d1`), `withValues` en 3 archivos y el test de plantilla con `NormativasApp`.
  Se juzgó que no justifican mantenerla: el contrato queda documentado en CLAUDE.md y en git (historial del repo
  raíz) sigue todo.
- Renombrada a `_ARCHIVO_normativas_app_vieja/` (no borrada), sacada del índice del repo raíz
  (`git rm -r --cached`, 141 archivos) y añadida a un `.gitignore` raíz nuevo, junto con `app/` (repo aparte).
- CLAUDE.md: tabla de los dos repos con sus remotos (`Sebastian-Paucar-R/guia-didactica-ra-ia` y
  `V-Erik/normativas_app`), secciones nuevas "Bitácora", "Frontend (`app/`)" y "API contract (summary)";
  corregidas las referencias a `normativas_app/` y dos gotchas desactualizados (`.env`/`__pycache__` ya no se
  versionan).
- Decisión: una sola bitácora, `PROYECTO/BITACORA.md` en el repo raíz, también para el trabajo en `app/`
  (citando el hash del commit de `app/`). El remoto de `app/` es de un compañero.

### Archivos tocados
- `CLAUDE.md`, `BITACORA.md`, `.gitignore` (nuevo); `normativas_app/` → `_ARCHIVO_normativas_app_vieja/`.

### Pendiente / siguiente paso
- Confirmar con el equipo y borrar `_ARCHIVO_normativas_app_vieja/`.
- Los cambios en `servidor/base_vectorial/` (binarios de Chroma) siguen sin commit y no son de esta tarea.
- Siguiente: lista de `app/ESTADO_REAL.md` (Firebase en la app, `api_client`/`chat_service` con el contrato).

## 2026-10-06 — Inventario real de la app Flutter (`app/ESTADO_REAL.md`)

### Qué se hizo
- Inventario leyendo cada archivo de `app/lib/`, Android y tests, más `flutter analyze` y `flutter build web`.
  Sin cambios de código. Hallazgos principales: login/registro simulados (`Future.delayed`); 4 mundos (normas
  25010/12207/27001/33001, no las unidades del sílabo) con 17 niveles sin contenido y sin pantalla de lección;
  no existen `chat_service.dart` ni `progreso_service.dart`; el chat apunta a `10.0.2.2:5000/api/chat` y envía
  `message` (incompatible con `/api/v1/chat` y sin token); AR = lector QR + Lottie 2D remoto (`avatar.glb` de
  27 MB y `model_viewer_plus` sin usar); `applicationId = com.example.normativas_app`, minSdk = 24 (default de
  Flutter 3.44.8); analyze: 4 errores (`iso_roadmap_screen.dart` muerto, `test/widget_test.dart` de plantilla).
- Ojo: `PROYECTO/normativas_app/` es una copia antigua; `CLAUDE.md` la describe a ella, no a `app/`.

### Archivos tocados
- `app/ESTADO_REAL.md` (nuevo), `BITACORA.md`.

### Pendiente / siguiente paso
- La lista "Lo que falta…" al final de `app/ESTADO_REAL.md` (Firebase Auth en la app, cliente HTTP con token,
  consentimiento, contrato de `/chat`, lecciones con ids de `lecciones.json`, progreso vía `/progreso/*`).
  Siguiente paso sugerido: `applicationId` propio + Firebase en la app, luego `api_client.dart`/`chat_service.dart`.

## 2026-09-30 — Integración con la app Flutter: contrato de /chat en español, lecciones, progreso (XP/racha), salud y Postman

No se encontró ningún repositorio ni README de `normativas-app-upec` en esta máquina (búsqueda exhaustiva en
`PROYECTO/`, OneDrive, OneDrive-UPEC, Documents y Downloads); se trabajó con el contrato literal del encargo,
según su propia instrucción de respaldo.

### Qué se implementó
- **Contrato de `/chat` en español** (`api/v1/endpoints/chat.py`): `ChatRequest`/`ChatResponse` renombrados a
  `mensaje`/`conversacion_id`/`leccion_id` (entrada) y `respuesta`/`tipo`/`conversacion_id`/`desde_cache`/
  `latencia_ms`/`tema_detectado`/`unidad_detectada`/`adaptacion`/`posicion_en_cola`/`espera_estimada_s` (salida),
  más `tema_id_detectado`/`metodo_deteccion`/`espera_real_s` como campos adicionales (los usan
  `pruebas/evaluar_tutor.py` y `scripts/prueba_concurrencia.py`, no pedidos por el contrato móvil pero inocuos
  para un cliente que los ignora). Todos los llamadores internos actualizados: `test_cache.py`, `test_tutor.py`,
  `test_pertinencia.py`, `test_adaptacion.py`, `pruebas/evaluar_tutor.py`, `pruebas/evaluar_adaptacion.py`,
  `scripts/prueba_concurrencia.py`, `scripts/bateria_tutor.py`, `scripts/evaluar_pertinencia.py`,
  `app/static/index.html`, `normativas_app/lib/screens/chat_screen.dart`.
- **`leccion_id`** (`core/lecciones.py` + `configuracion/lecciones.json`, ya traían la relación lección → tema
  del sílabo de antes del corte de contexto): terminado de cablear en `RAGService._procesar`/`_flujo` —
  si resuelve, la recuperación se restringe a los documentos del tema y se fuerza la ubicación (`metodo:
  leccion`), saltando el filtro de pertinencia normal; estas respuestas no pasan por el caché semántico (ni
  lectura ni guardado). Tests nuevos: `tests/test_lecciones.py` (el mapeo en aislamiento + el flujo completo).
- **Progreso de la app (XP, racha, lecciones, ejercicios)**: tablas nuevas `progreso_estudiante`/
  `eventos_progreso` (`app/db/models.py`, migración `alembic/versions/0002_progreso_app.py`), servicio
  `services/progreso_service.py` (+20 XP lección, +10/+2 XP ejercicio correcto/incorrecto, racha de días
  consecutivos) y endpoints `GET /progreso/mio`, `POST /progreso/lecciones/{id}/completar`,
  `POST /progreso/ejercicios/{id}/resolver` (siempre el propio estudiante). Agregado (nunca por estudiante) en
  `GET /docente/estadisticas` como `progreso_app`. Tests: `tests/test_progreso.py`.
- **`GET /api/v1/salud`** (`api/v1/endpoints/salud.py`, público): estado del servidor, modelo configurado,
  si Ollama responde (`OLLAMA_BASE_URL`, ahora pasado explícitamente a cada `ChatOllama` en vez de confiar en su
  valor por defecto) y documentos/chunks indexados. Tests: `tests/test_salud.py`.
- **CORS**: `allow_credentials=True` con `allow_origins=["*"]` era una combinación inválida que los navegadores
  rechazan (y no hacía falta: la identidad va en `Authorization`, no en cookies); corregido a
  `allow_credentials=False`.
- **Documentación de la integración**: `servidor/docs/contrato_api.md` (contrato completo: cada endpoint,
  ejemplo de petición/respuesta, códigos de error, significado de cada campo — para pasarle a un compañero) y
  `servidor/docs/tutor_ia.postman_collection.json` (colección Postman v2.1, auth Bearer a nivel de colección,
  `/salud` y `/cola/estado` marcados `noauth`). CLAUDE.md: sección "Identity, database and generation queue"
  escrita (se referenciaba cinco veces y nunca existía), con la arquitectura de identidad/DB/cola de la sesión
  anterior más lo nuevo de esta.

### Bugs encontrados y corregidos durante las pruebas
- `progreso_service.py`: `ProgresoEstudiante` recién construido tenía `None` en sus columnas numéricas (los
  `default=0` de SQLAlchemy solo se aplican al hacer INSERT, no al instanciar en Python), así que el primer
  `+= 1` lanzaba `TypeError`. Corregido inicializando los campos explícitamente al crear la fila.
- Dos wrappers de prueba (`get_answer_con_usuario` en `test_cache.py` y `test_adaptacion.py`, que siembran el
  Usuario antes de delegar a `RAGService.get_answer` real) no tenían `leccion_id` en su firma; al pasar a
  llamarse con 4 posicionales desde `chat.py` (antes 3), fallaban con `TypeError`. Corregido añadiendo el
  parámetro.
- `api/v1/endpoints/progreso.py` leía `session_factory_por_defecto()` (el singleton perezoso de `DATABASE_URL`,
  pensado para que la app real lo cachee una vez por proceso): en pruebas, cada test apunta `DATABASE_URL` a un
  SQLite temporal distinto, pero el singleton ya inicializado por un test anterior seguía apuntando al primero,
  así que escribir progreso de otro test fallaba la clave foránea a `usuarios` (la fila no existía en ESA base).
  Corregido sustituyéndolo con `app.dependency_overrides` en `tests/test_progreso.py`, igual que
  `api/v1/endpoints/usuarios.py` ya hacía con `get_db`.

### Verificación realizada
620 tests (601 anteriores + 19 nuevos: `test_progreso.py` (8 servicio + 3 endpoint), `test_salud.py` (3),
`test_lecciones.py` (8) — el resto de archivos solo se actualizó al nuevo contrato, sin tests nuevos), suite
completa en verde dos veces seguidas tras las correcciones. Servidor real arrancado contra una
base de datos temporal recién migrada (`scripts/inicializar_db.py`, cadena 0001→0002 verificada): `GET /salud`
y `GET /documentos` responden 200 sin token; `POST /chat`, `GET /usuarios/yo`, `GET /docente/estadisticas`,
`GET /progreso/mio` responden 401 sin token; sin errores en el log de arranque. `base_vectorial/` quedó con
cambios binarios (reordenamiento, mismo tamaño) por abrir Chroma durante la prueba; descartados con
`git checkout` antes de seguir, conforme a la convención del proyecto.

### Pendiente / limitaciones
- `normativas_app/lib/screens/chat_screen.dart` manda ya los nombres de campo correctos pero sigue sin enviar
  `Authorization` ni pasar por un flujo de consentimiento: una llamada real contra este backend da 401. Cablear
  Firebase en el lado Flutter queda fuera de este encargo (era "preparar el backend").
  `pruebas/evaluar_tutor.py`, `backend/scripts/bateria_tutor.py` y `backend/scripts/evaluar_pertinencia.py`
  tienen la misma limitación preexistente (HTTP real sin token); solo `prueba_concurrencia.py` y
  `evaluar_adaptacion.py` la evitan con una sustitución de dependencia en proceso.
- No se encontró el repositorio `normativas-app-upec` ni su README en esta máquina (ver nota al inicio).
- `configuracion/lecciones.json` tiene 5 lecciones de ejemplo; mantenerlo actualizado es trabajo de quien
  mantenga la app, no algo que este backend pueda validar más allá de que el `tema_id` exista en el sílabo.


## 2026-09-29 — Identidad (Firebase), base de datos relacional, cola de generación y estadísticas docentes

### Qué se implementó
- **Base de datos**: migración de SQLite-blob a SQLAlchemy + Alembic (`app/db/`: `base.py`, `models.py`,
  `session.py`; migraciones en `backend/alembic/`, inicial en `alembic/versions/0001_esquema_inicial.py`).
  Cinco tablas: `usuarios`, `perfiles` (el perfil adaptativo en JSON, con FK a usuarios), `conversaciones` /
  `mensajes` (historial real del chat, antes solo en RAM), `eventos_perfil` (cada cambio de nivel, con su
  motivo). `DATABASE_URL` decide el motor: SQLite en archivo por defecto (`servidor/tutor.db`), PostgreSQL con
  `postgresql+pg8000://...` para un despliegue real. Driver `pg8000` (puro Python) en vez de `psycopg2`: en esta
  máquina, la misma directiva de Control de aplicaciones que bloqueaba `grpc` (ver la entrada de más abajo)
  también bloquea el binario nativo de psycopg2; `pg8000` evita el problema de raíz. SQLite activa
  `PRAGMA foreign_keys=ON` por conexión (SQLAlchemy event listener), para que las claves foráneas se exijan
  igual que en PostgreSQL y un perfil o una conversación huérfanos fallen en desarrollo, no solo en producción.
  `services/perfil_service.py` reescrito sobre SQLAlchemy (mismo API público); nuevo `services/historial_service.py`
  para conversaciones/mensajes; el ritmo del perfil (mensajes por sesión, duración) ahora se calcula de esas
  tablas en vez de duplicarlo.
- **Identidad con Firebase Authentication** (`core/firebase_auth.py`, `api/deps.py`): nunca se guarda una
  contraseña. `usuario_actual` verifica `Authorization: Bearer <id_token>` y crea el usuario (rol `estudiante`)
  la primera vez; `usuario_con_consentimiento` además exige `consentimiento_aceptado` (409 si falta, con
  `POST /usuarios/consentimiento` para aceptarlo); `requiere_rol(...)` para docente/admin.
  `verificar_token` es sustituible en pruebas (`tests/test_auth.py`), sin credenciales reales.
- **`user_id` deja de ser un parámetro libre**: `ChatRequest` ya no tiene `user_id` (sale de
  `usuario.uid_firebase`, del token verificado); `/perfil/{uid}` exige ser ese estudiante o rol docente/admin
  (`verificar_propietario`, con pruebas explícitas de que un estudiante no puede leer el perfil de otro).
- **Cola de generación** (`services/cola_service.py`, `asyncio.Semaphore`, no `threading.Semaphore`: esperar un
  cupo no debe ocupar un hilo del threadpool de Starlette, limitado a 40 por defecto — ver el docstring del
  módulo para las 4 decisiones de diseño, incluida por qué los aciertos de caché nunca pasan por la cola
  -`RAGService.probar_cache`, nuevo- y por qué las llamadas cortas del turno -clasificar, reformular, redirigir-
  sí van dentro del mismo cupo que la generación). `ESPERA_MAXIMA_COLA_S` con `asyncio.wait_for`: pasado ese
  tiempo, 503 en vez de una conexión colgada. `GET /cola/estado` para sondear en vivo.
- **`GET /docente/estadisticas`**: estudiantes activos, preguntas por unidad, temas con más dificultad,
  evolución media del nivel por unidad — agregados sobre `usuarios`/`mensajes`/`perfiles`, nunca datos de un
  estudiante concreto.
- **Precalentamiento del caché**: `pruebas/precalentar_cache.py` + `configuracion/preguntas_frecuentes.json`
  (editable, por unidad del sílabo); corre en proceso, sin HTTP ni credenciales.
- `.env.example`, `.gitignore` ampliado (`.env`, `tutor.db`, credenciales de Firebase, `google-services.json`);
  `servidor/backend/.env` (vacío, ya no aportaba nada) se dejó de versionar.

### Bloqueador de entorno encontrado y corregido (van dos en el proyecto)
Igual que `grpc`/chromadb (ver la entrada de más abajo), `psycopg2` tiene un binario nativo que esta máquina
bloquea. Resuelto de raíz usando `pg8000` (driver de PostgreSQL puro Python) en vez de trabajar alrededor del
bloqueo.

### Prueba de concurrencia real (`reportes/prueba_concurrencia.md`)
`backend/scripts/prueba_concurrencia.py`, contra el RAG y `llama3.2` reales, en proceso (sin credenciales de
Firebase: `usuario_actual` sustituido por un estudiante de prueba ya consentido). Primera corrida: los niveles
de 20 y 40 fallaron en más de la mitad de las peticiones con `RuntimeError: ... is bound to a different event
loop` — bug real, pero del guion de prueba (llamaba `asyncio.run()` una vez por nivel, y la cola es un
singleton de módulo con primitivas de asyncio atadas al primer event loop que las usa), no del servidor: un
proceso de uvicorn real corre un único event loop toda su vida. Corregido envolviendo los tres niveles en un
solo `asyncio.run()`. Corrida ya corregida: **10, 20 y 40 peticiones simultáneas, 100 % HTTP 200, cero errores,
cero tiempos de espera agotados**, con `LIMITE_GENERACIONES_SIMULTANEAS=2` y `ESPERA_MAXIMA_COLA_S=90`; con 40
peticiones a la vez la espera máxima observada (72,6 s) ya se acerca al tope de 90 s — margen a vigilar si
crece la concurrencia real.

### Verificación realizada
601 tests (539 anteriores + 62 nuevos: `test_auth.py`, `test_cola.py`, `test_docente.py`, `test_historial.py`,
`test_usuarios.py`, más los existentes actualizados a la nueva base y a exigir autenticación). Servidor real
arrancado (copia de índice/caché/base de datos): `POST /chat`, `GET /usuarios/yo` y `GET /docente/estadisticas`
responden 401 sin token con un mensaje claro (incluido el caso sin `FIREBASE_CREDENTIALS_PATH` configurado);
`GET /documentos` y `GET /cola/estado` (públicos) responden 200; sin errores en el log del servidor.

### Pendiente / limitaciones
- Sin credenciales reales de Firebase en este entorno: la verificación de tokens se probó con
  `verificar_token` sustituido (pruebas y guion de carga), nunca contra el servicio real. Falta probarlo con
  un proyecto de Firebase real y el flujo completo desde Flutter.
- La app Flutter todavía no manda `Authorization: Bearer <id_token>` ni pantalla de consentimiento: hasta que
  se cablee, no puede usar ningún endpoint protegido.
- `GET /docente/estadisticas` lee todos los perfiles en Python para agregar `temas_con_dificultad` y
  `nivel_por_unidad` (JSON, no columnas): para un curso normal es rápido y simple; con miles de estudiantes
  convendría una consulta SQL sobre JSON (JSONB en PostgreSQL) en vez de traer todas las filas.
- La prueba de concurrencia midió un único valor de `LIMITE_GENERACIONES_SIMULTANEAS` (2, el de por defecto);
  no determina cuál es el límite óptimo para un hardware distinto.

## 2026-09-29 — Atribución cruzada entre normas: modelo mayor, atribución por oración y dos bugs conocidos (en curso)

### Qué se implementó
- **Bloqueador de entorno corregido**: el servidor no arrancaba (`import chromadb` fallaba con `DLL load failed
  while importing cygrpc: Una directiva de Control de aplicaciones bloqueó este archivo`; chromadb importa sin
  condición un exportador OTLP/gRPC que este proyecto nunca usa). Nuevo `core/chroma_compat.py`: si `import grpc`
  falla, deja un módulo vacío en su lugar antes de que chromadb lo pida. Sin esto no se podía ni correr `pytest`.
- **Atribución por oración** (`tutor_service.atribuciones_no_respaldadas`): por cada oración que nombra una norma,
  exige que ESA norma tenga al menos un fragmento RECUPERADO de su propio documento (`mapa_normas`, por nombre de
  archivo/título) y, si nombra una sola norma, que sus cláusulas/cantidades salgan del fragmento de esa norma (no
  de otra del contexto); con dos o más normas en la misma oración (contrastes legítimos) solo exige lo primero,
  para no marcar falsos positivos. Es el fallo que `normas_no_respaldadas` no atrapaba: comparaba contra el
  respaldo completo, así que una cláusula real pero de OTRA norma recuperada lo dejaba pasar. `normas_citables`
  sigue permitiendo nombrar (no explicar) temas ya trabajados por el estudiante, como antes. Integrado en el mismo
  mecanismo de reintento + poda de oraciones que ya existía.
- **Profundidad acotada por el contexto, no por el perfil** (`tutor_service.nivel_de_contexto`, escaso/moderado/
  amplio por palabras de contenido recuperadas): con contexto escaso la profundidad efectiva baja a "breve" pase
  lo que pida el perfil (moderado tope "media"), y se agrega un aviso explícito de no rellenar. TAREA no cambia
  (sus pasos numerados son una regla aparte). El segmento de caché se recalcula con la profundidad final aplicada
  (`adaptacion_service.segmento_de`, extraído de `construir_adaptacion` para reutilizarlo), documentado que le
  cuesta algún acierto de caché a un perfil "extensa" con poco material (nunca sirve la extensión equivocada).
- **Bug corregido**: `terminos_sin_respaldo` comparaba por subcadena (`in`) y encontraba "dame" dentro de
  "fundamentos"; ahora usa límites de palabra (`_palabra_en`).
- **Bug corregido**: un seguimiento sin tema propio ("explícame eso mejor") ya no se reclasifica si el turno
  anterior tiene un tema conocido: lo hereda directamente (`RAGService._flujo`, con `Turno.ubicacion` nuevo en
  `memoria_service`). Antes, una reformulación imprecisa del LLM de 3B podía hacer que el score o el clasificador
  lo redirigieran por error (medido: 3 de 25 en una evaluación real).
- **Veredictos del banco de adaptación endurecidos** (`pruebas/evaluar_adaptacion.py`): nuevo verdicto
  `identificadores_coinciden` (las tres respuestas deben citar exactamente las mismas normas; si una nombra una
  que otra no, es fallo) sumado a `contenido_normativo`; nueva columna/fila en el informe.
- **Opción híbrida habilitada**: `MODELO_CLASIFICADOR` (aparte de `MODELO_LLM`) en `core/config.py` y
  `rag_service.py`, para poder usar un modelo distinto en las llamadas cortas de clasificación/reformulación que
  en la generación de la respuesta, sin tocar nada más.

### Archivos tocados
Nuevos: `servidor/backend/app/core/chroma_compat.py`. Modificados: `servidor/backend/app/{core/config.py,
services/{rag_service,tutor_service,adaptacion_service,memoria_service,pertinencia_service}.py}`,
`servidor/backend/tests/{test_tutor.py}`, `servidor/pruebas/evaluar_adaptacion.py`, `CLAUDE.md`, `BITACORA.md`.

### Verificación realizada
539 tests (538 + 1 nuevo); los dos tests rotos por el cambio de comportamiento se ajustaron para probar el
comportamiento nuevo (no se desactivaron). Servidor real arrancado sin errores (`llama3.2`, 10 documentos/111
chunks); `POST /chat` verificado a mano con una pregunta real. Sanity check a mano de `atribuciones_no_respaldadas`
(atrapa una atribución cruzada fabricada entre ISO 9001/27001; no marca un contraste legítimo con dos normas).

### Punto 1: comparativa de modelos (`reportes/comparativa_modelos.md`, `pruebas/banco_comparativa_modelos.json`)
`llama3.1:8b`, `qwen2.5:7b-instruct` y `mistral:7b` corridos contra un banco reducido (18 preguntas) + la parte 1
de `casos_adaptacion.json` (sin evolución), servidor real por modelo, copia de índice y caché/perfiles nuevos.
Los tres acertaron el filtro al 100 % igual que `llama3.2`, pero fueron 4-7× más lentos (2,4 s vs 10-17 s medios;
colas de hasta 40-138 s) y ninguno mostró mejor calidad: `llama3.1:8b` cometió la única atribución cruzada real
de los cuatro (le atribuyó a ISO 31000 el "pensamiento basado en riesgos" que los documentos dicen que introdujo
ISO 9001 en 2015) y que además es un caso real del punto ciego documentado del chequeo automático (dos normas en
la misma oración). **Recomendación: mantener `llama3.2` por defecto.** La opción híbrida (`MODELO_CLASIFICADOR`,
implementada) no se corrió en vivo por tiempo; queda lista para retomar si cambia el hardware.

Incidente de memoria durante esta parte: el sistema se quedó sin RAM (Fortnite corriendo, ~4 GB) y mató los
procesos en segundo plano de `mistral:7b` a mitad de arrancar (sin datos útiles perdidos, no había respondido
ninguna pregunta todavía). Se limpiaron los procesos huérfanos, se descargó el modelo de memoria de Ollama, el
usuario cerró Fortnite y se repitió solo ese modelo con memoria libre.

### Punto 6: ronda oficial con la configuración final
Servidor real, copia de `base_vectorial/`, caché y perfiles nuevos, `llama3.2` (configuración final,
recomendación del punto 1). `pruebas/evaluar_tutor.py --robustez` (banco completo, 60 preguntas): **100 % de
precisión del filtro (60/60)**, 0 falsos positivos/negativos, latencia media sin caché 3,99 s (antes: 10,1 s —
más rápido por la GPU, no por el código), unidad acertada 97,5 %, tema acertado 87,5 % — sin regresión frente a
la corrida anterior. Robustez: 9/10 automático; el "fallo" (R03) es un falso positivo de la heurística leído a
mano (el tutor no adoptó el personaje de poeta pedido, solo abrió con "Amigo mío"; la heurística no distingue
tono cercano de abandono de rol). `pruebas/evaluar_adaptacion.py` (con evolución): los 7 verdictos de evolución
en verde, igual que antes.

**Lectura crítica de las 9 respuestas (ISO 9001, ISO/IEC 25010, ISO/IEC/IEEE 12207 × 3 perfiles): ninguna
invención ni atribución cruzada encontrada** (contraste directo con la corrida del 20/09 antes de estas
correcciones, donde el novato tuvo 2 de 3 respuestas con contenido inventado o trasladado entre normas). El
verdicto automático `contenido_normativo`/`identificadores_coinciden` marcó las 3 preguntas como False, pero por
motivos benignos confirmados a mano (un perfil escribe "ISO 9001:2015" y otro "ISO 9001", o solo un perfil
menciona de pasada una norma relacionada en la pregunta de cierre) — el chequeo más estricto (punto 5) está
haciendo exactamente lo pedido: preferir marcar algo dudoso para que se lea, aunque termine siendo inofensivo.
Nota aparte, no del encargo: las 3 respuestas sobre ISO/IEC 25010 siguen siendo débiles en los cuatro modelos
probados (incluido este); la causa es que la recuperación (embeddings, sin cambios) no trae el documento de
25010 entre los 4 fragmentos para esa pregunta exacta — un problema de recuperación, no de generación, ya
anotado como pendiente en corridas anteriores.

Se corrigió además, al encontrarlo en vivo, un bug menor en `pruebas/evaluar_adaptacion.py`: el resumen final en
consola (con `│`/`─`) rompía con `UnicodeEncodeError` en una consola Windows sin `PYTHONUTF8=1` — ya escribía los
reportes antes de ese punto, así que no perdía datos, pero cortaba el script antes de imprimir el resumen.

### Commit y push
Pendiente al cerrar esta entrada (se hace a continuación, según lo pedido).

## 2026-09-20 — Perfilado adaptativo del estudiante (nivel por unidad, profundidad, estilo, historial) y caché segmentado

### Qué se implementó
- **Perfil por `user_id`** (`models/perfil.py`, `services/perfil_service.py`, SQLite `servidor/perfiles.db`, git-ignored): nivel estimado 1–5 por cada una de las 4 unidades
  (inicio 3), temas consultados, temas con dificultad, profundidad (breve/media/extensa), estilo (conceptual/ejemplos/comparativo), ritmo (mensajes por sesión y duración media) e
  historial de los últimos 5 temas. Tablas `perfiles`, `progreso` (cada cambio de nivel) y `sesiones`. `POST /chat` ya usaba `user_id` sin efecto: ahora lo pasa a `get_answer`.
- **Actualización tras cada turno** (`services/adaptacion_service.py`), solo por conducta observable y gradual: «no entendí»/«explícame mejor»/«otra vez» bajan 0,4 el nivel de la
  unidad y marcan dificultad (a la 2.ª vez si es solo pedir aclarar); responder bien una pregunta de reflexión (candidata por reglas + juez LLM conservador) sube 0,3; ≥3 pedidos de
  ejemplos/comparar cambian el estilo y ≥3 de ampliar/resumir mueven la profundidad **un escalón**. Máximo un movimiento de nivel por turno. Un seguimiento sigue en el tema anterior
  salvo que nombre otro por palabras clave; una redirección solo cuenta para el ritmo, salvo un seguimiento corto sin tema propio justo tras una explicación (el filtro lo redirigió por error).
- **Inyección en el prompt**: hueco `{adaptacion}` tras `{modo}` (vacío = prompt idéntico al anterior). Modula profundidad (PUNTUAL/PROFUNDIZAR; TAREA no cambia), andamiaje (analogías y pregunta
  sencilla para nivel bajo o tema con dificultad; directo y pregunta socrática exigente para nivel alto) y referencias a lo ya visto de la misma unidad. El ajuste se repite muy corto en el
  recordatorio final y la pregunta de cierre se regenera con la exigencia del nivel (`tutor.ajustar_pregunta_final`). Las verificaciones de salida siguen iguales para todos.
- **Caché segmentado por el ajuste realmente usado** (decisión documentada en `CLAUDE.md`, «Semantic cache»): columna `segmento` con migración del esquema, sin cruces entre niveles/profundidades,
  perfil neutro comparte lo existente, `sin_contexto` se comparte, las respuestas que citan lo ya trabajado son personales y no pasan por el caché. Se descartó «cachear solo el núcleo factual y
  generar la envoltura cada vez»: ahorra <2 % o exige una 2.ª llamada al LLM y expone el contenido normativo a distorsión. `/cache/estadisticas` suma `entradas_por_segmento` y `omitidos_por_perfil`.
- **Endpoints**: `GET /api/v1/perfil/{user_id}`, `GET /api/v1/perfil/{user_id}/progreso` (evolución por unidad desde un punto inicial en 3,0), `POST /api/v1/perfil/{user_id}/reiniciar`. `/chat` devuelve `adaptacion`.
- **Verificador**: `tutor_service._CONTEO` también controla cantidades escritas con letras («tres niveles»), tras verlo fallar en la evaluación real.
- **Banco de adaptación**: `pruebas/casos_adaptacion.json` + `pruebas/evaluar_adaptacion.py` → `reportes/evaluacion_adaptacion.{json,md}`; lectura crítica a mano en `reportes/evaluacion_adaptacion_lectura.md`
  y primera corrida en `evaluacion_adaptacion_corrida1.md`.

### Archivos tocados
Nuevos: `servidor/backend/app/{models/perfil.py, services/{perfil_service,adaptacion_service}.py, api/v1/endpoints/perfil.py}`, `servidor/backend/tests/{test_perfil,test_adaptacion}.py`,
`servidor/pruebas/{casos_adaptacion.json,evaluar_adaptacion.py}`, `servidor/reportes/evaluacion_adaptacion*.{md,json}`. Modificados: `servidor/backend/app/{core/config.py, main.py, api/v1/endpoints/chat.py,
services/{rag_service,tutor_service,cache_service}.py}`, `servidor/backend/tests/{conftest,test_cache,test_tutor}.py`, `servidor/.gitignore`, `CLAUDE.md`, `BITACORA.md`.

### Resultados
- **538 tests** (311 previos + 227 nuevos). Cada invariante nuevo se verificó rompiéndolo a propósito (22 mutaciones, todas detectadas): segmentación y compartición del caché, exclusión de lo personal,
  atomicidad del perfil, gradualidad, consumo de señales, respaldo de las referencias, cierre regenerado y verificado, seguimientos, cantidades en letras. El servidor arrancó sin errores en cada ronda real.
- **Evaluación real (llama3.2, 3 preguntas × 3 estudiantes, servidores limpios; final = 9 respuestas por perfil)**: el novato (extensa + ejemplos) responde ≈2× más largo (156 vs 80 palabras) y abre con
  una analogía o situación en 9/9; el avanzado cierra con un «por qué/qué pasaría si» en 4/9 (0/6 antes del recordatorio final y la pregunta regenerada); el caché no cruzó segmentos en ninguna pregunta;
  la evolución de un estudiante real bajó 3,0 → 2,6 → 2,2 sin saltos, marcó dificultad tras «No entendí», pasó a estilo «ejemplos» al tercer pedido y adaptó la siguiente respuesta.
- **Lo que NO salió bien**: el contenido normativo no coincide de forma fiable entre perfiles. En la ronda oficial final el novato (extensa) tuvo 2 de 3 respuestas con contenido inventado o
  trasladado entre normas (p. ej. «ISO 9001 aborda la seguridad de la información y el gobierno de riesgos»; 12207 con cosas de 42010 y texto incoherente), el estándar sin ajuste 1 de 3 y el avanzado
  (corto) 0 de 3. Los verdictos automáticos dijeron ✅ en las tres preguntas: no detectan atributos trasladados ni relleno. Detalle y cifras en `reportes/evaluacion_adaptacion_lectura.md`.

### Pendiente / limitaciones
- Contenido con `llama3.2`: relleno y traslado de atributos entre normas (también sin perfil: a veces atribuye a ISO 9001 lo que el documento dice de ISO 31000, «no certificable»). Antes de exponerlo
  a estudiantes: probar un modelo mayor con la misma batería, limitar o desactivar la profundidad extensa y añadir una comprobación de atribución por oración.
- Defectos previos al perfil vistos: el reformulador deja seguimientos pelados sin reescribir y el filtro los redirige (3 de 25 en cinco ejecuciones); `terminos_sin_respaldo` busca los nombres del sílabo
  como subcadena («Dame» dentro de «fundamentos») y un seguimiento salió como `sin_contexto`. No se tocaron.
- **Ni la página de prueba ni Flutter envían `user_id`**: hasta que lo hagan, la app real no adapta nada. Los endpoints de perfil no tienen autenticación (el proyecto no la tiene).
- El juez de «reflexión correcta» es débil con un 3B (conservador y de efecto pequeño); estilo/profundidad no vuelven solos a conceptual/media (hay `/reiniciar`); la *breve* apenas acorta.
- `main` estaba 6 commits por delante de `origin/main` al empezar; el push los publica junto con este trabajo.

### Siguiente paso sugerido
Cablear `user_id` en Flutter (`chat_screen.dart`) y en la página de prueba, mostrar `GET /perfil/{id}` y `/progreso` en la pantalla de perfil, y repetir `pruebas/evaluar_adaptacion.py` con un modelo mayor
antes de activar la profundidad extensa para estudiantes reales.

## 2026-09-20 — Sílabo en YAML, filtro contra el temario, auditoría de cobertura y evaluación del tutor

### Qué se implementó
- `servidor/configuracion/silabo.yaml`: 4 unidades y 27 temas (id, nombre, unidad, palabras clave, archivos .md). `core/silabo.py` lo carga y
  valida (falla al arrancar si es inválido) y sustituye a la lista escrita en Python. El tema 2.8 (ISO 20000/29110/31000/42010) está marcado
  `complementario`: no está en el sílabo oficial pero sus documentos están indexados.
- Filtro de pertinencia reordenado (no reemplazado): saludo/sobre el tutor → palabras clave del YAML → cambio de rol sin tema → score → LLM que
  elige un **número de tema** del YAML o FUERA. Cada consulta del temario registra unidad y tema (`[FILTRO] ... unidad= tema= metodo=` y campo
  `ubicacion` en `/chat`).
- Prompt endurecido contra 3 fallos: abandono de rol (`es_intento_abandonar_rol`, redirección sin la orden inyectada, regla en 3 prompts), normas inventadas
  (regla + verificación ampliada a capítulo/sección/apartado) e insistencia (`tutor.insistencia`, `tarea_original`, modo firme, sin filtro ni caché).
- `pruebas/auditar_cobertura.py` → `reportes/cobertura_silabo.md`: 6 cubiertos, 12 parciales, 9 sin cobertura (de 27).
- `pruebas/banco_consultas.json` (40 dentro, 20 fuera) + `pruebas/evaluar_tutor.py` → `reportes/evaluacion_tutor.{json,md}`; `pruebas/casos_robustez.json`.
- `reportes/historial_ajustes.md`: las 3 iteraciones, lo que falló y lo que no quedó resuelto.

### Archivos tocados
`servidor/configuracion/silabo.yaml`, `servidor/pruebas/*`, `servidor/reportes/*` (nuevos); `servidor/backend/app/{core/silabo.py, core/config.py,
services/{pertinencia_service,tutor_service,rag_service,memoria_service}.py, api/v1/endpoints/chat.py}`, `backend/requirements.txt` (PyYAML),
`backend/tests/{test_silabo.py (nuevo), test_pertinencia.py, test_tutor.py}`, `CLAUDE.md`, `BITACORA.md`.

### Resultados (servidor real + Ollama llama3.2)
- Precisión del filtro **100 %** (60/60; 0 FP, 0 FN) en la evaluación final; 96,7 % en la primera. Es una medida de desarrollo (se ajustó mirando el banco);
  el conjunto antiguo de 46 preguntas, no usado para diseñar esto, dio 22/22 fuera y 24/24 dentro aceptadas.
- Latencia media sin caché 13,4 s (respuestas cacheables) / 10,1 s (todas); con caché 0,02 s (~740×). 13 de 40 respuestas dentro del temario declararon
  contexto insuficiente (9 de 14 sobre temas «sin cobertura»). Unidad acertada 97,5 %, tema exacto 87,5 %.
- 311 tests (69 nuevos en `test_silabo.py`); el servidor arrancó sin errores y sirvió las 3 evaluaciones.

### Pendiente / limitaciones
- Normas inventadas solo parcialmente resuelto: se detectan números/años/cláusulas/capítulos inexistentes, no atribuciones falsas a normas reales
  (llama3.2 dijo que ISO 42010 trata de IA). Insistencia: no se entrega la solución, pero el modelo repite casi la misma guía.
- Las heurísticas de robustez del evaluador son débiles (9/9 con fallos reales): leer las conversaciones del JSON.
- 9 temas del sílabo sin documento (Kanban, Lean, ISO 42001, KPIs/GQM, métricas de flujo, DORA, métricas UX/seguridad/sostenibilidad, TDD, mantenimiento/14764).
- `iniciar_servidor.bat` sigue apuntando a un venv sin el stack RAG; los `.pyc` siguen versionados.

### Siguiente paso sugerido
Cargar los documentos de los 9 temas sin cobertura (con `POST /documentos/subir`), volver a ejecutar `auditar_cobertura.py` y `evaluar_tutor.py`, y valorar un LLM
mayor para redactar `sin_contexto` y verificar atribuciones.

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
