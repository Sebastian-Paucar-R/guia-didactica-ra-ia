# Entrega del backend para la app Flutter

Para: quien integra la app Flutter (`normativas_app`) con este backend y no ha visto antes el servidor.

Todo lo que aparece aquí se leyó del código o se ejecutó de verdad. Los JSON de ejemplo **no son inventados**: se
capturaron el 2026-10-09 llamando a la API real (en proceso, con Ollama `llama3.2` y el índice real de 10
documentos). Para no tocar datos reales se usaron una base de datos, un caché y una copia del índice temporales.
Lo único simulado fue la verificación de Firebase (un token de prueba que siempre devuelve el uid `uid-ana-123`).
Los textos del tutor van tal cual los generó el modelo, recortados en algún caso.

Documentos relacionados:

- `docs/contrato_api.md`: el contrato de la API completo, con también los endpoints de docente, caché y documentos.
- `docs/tutor_ia.postman_collection.json`: colección de Postman con todas las rutas.
- `reportes/prueba_concurrencia.md` y `reportes/comparativa_modelos.md`: de ahí salen los números de las secciones
  4 y 5.

Rutas de archivo: salvo que se diga otra cosa, son relativas a la carpeta `servidor/` del repositorio
`guia-didactica-ra-ia`.

---

## Índice

1. [Levantar el backend en tu PC](#1-levantar-el-backend-en-tu-pc)
2. [Contrato de los endpoints que usa la app](#2-contrato-de-los-endpoints-que-usa-la-app)
3. [Autenticación](#3-autenticación)
4. [Los campos de cola](#4-los-campos-de-cola)
5. [Latencias y timeouts](#5-latencias-y-timeouts)
6. [Qué cambiar en `lib/services/chat_service.dart`](#6-qué-cambiar-en-libserviceschat_servicedart)
7. [Los 9 temas del sílabo sin documentación](#7-los-9-temas-del-sílabo-sin-documentación)

---

## 1. Levantar el backend en tu PC

### 1.1 Requisitos

| Qué | Versión / detalle | Para qué |
|---|---|---|
| Python | **3.14** (con la que está probado y fijado `backend/requirements.txt`) | El servidor (FastAPI + uvicorn) |
| [Ollama](https://ollama.com/download) | cualquiera reciente | Ejecuta el modelo de lenguaje en local |
| Modelo `llama3.2` | ~2 GB | El modelo por defecto (`MODELO_LLM`) |
| Internet en el primer arranque | — | Descargar el modelo de embeddings `sentence-transformers/all-MiniLM-L6-v2` de Hugging Face (una sola vez; después queda en caché) |
| Credencial de Firebase (JSON de cuenta de servicio) | proyecto **`tutor-ia-upec-ec787`**, el mismo de `lib/firebase_options.dart` | Verificar los tokens que manda la app |
| Git | — | Clonar el repositorio |

No hace falta instalar ninguna base de datos: por defecto se usa SQLite en el archivo `servidor/tutor.db`, que se
crea solo.

### 1.2 Ollama y el modelo

1. Instala Ollama. En Windows queda corriendo como servicio en `http://localhost:11434`.
2. Descarga el modelo:
   ```
   ollama pull llama3.2
   ```
3. Comprueba que está:
   ```
   ollama list
   ```
   Debe aparecer una línea `llama3.2:latest ... 2.0 GB`.

### 1.3 Código y dependencias

```
git clone https://github.com/Sebastian-Paucar-R/guia-didactica-ra-ia.git
cd guia-didactica-ra-ia\servidor\backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

`iniciar_servidor.bat` activa automáticamente un entorno virtual en `backend\venv` si existe, así que conviene
crearlo justo ahí.

### 1.4 Credencial de Firebase

El backend no maneja contraseñas: solo verifica el `id_token` que Firebase le da a la app. Para eso necesita la
clave de una cuenta de servicio del **mismo** proyecto de Firebase que usa la app (`tutor-ia-upec-ec787`).

- Si tienes acceso a la consola: **Configuración del proyecto → Cuentas de servicio → Generar nueva clave privada**.
  Se descarga un JSON.
- Si no lo tienes, pídele a Sebastián el JSON por un canal privado.

Guárdalo **fuera** del repositorio, por ejemplo en `C:\credenciales\tutor-ia-firebase.json`. Nunca lo subas: el
`.gitignore` excluye `*firebase-adminsdk*.json`, pero solo si conserva ese nombre.

En Firebase también tiene que estar activado el proveedor **Correo/contraseña** (y Google, si la app lo usa):
**Authentication → Sign-in method**.

### 1.5 Variables de entorno mínimas

Solo hace falta **una**. Todo lo demás tiene un valor por defecto que funciona (ver `backend/app/core/config.py`).

```
FIREBASE_CREDENTIALS_PATH=C:/credenciales/tutor-ia-firebase.json
```

> **Ojo con dónde va el `.env`.** `config.py` lee el archivo `.env` de la **carpeta desde la que arrancas el
> proceso**, no el de una ruta fija (se comprobó ejecutándolo). `iniciar_servidor.bat` arranca desde `servidor/`,
> así que el `.env` tiene que estar en **`servidor/.env`**. Si lo pones solo en `servidor/backend/.env` (lo que dice
> `backend/.env.example`), el servidor arrancado con el `.bat` **no lo lee**. Lo más seguro es tener el mismo
> archivo en las dos carpetas, o definir la variable en la consola (`set FIREBASE_CREDENTIALS_PATH=...`) antes de
> arrancar.

Variables opcionales que puedes tocar:

| Variable | Por defecto | Cuándo cambiarla |
|---|---|---|
| `MODELO_LLM` | `llama3.2` | No la cambies: la sección 5 explica por qué |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Si Ollama corre en otra máquina |
| `LIMITE_GENERACIONES_SIMULTANEAS` | `2` | Respuestas que se generan a la vez (sección 4) |
| `ESPERA_MAXIMA_COLA_S` | `120` | Segundos máximos en cola antes de responder 503 |
| `DATABASE_URL` | SQLite en `servidor/tutor.db` | Solo para PostgreSQL |

### 1.6 Crear la base de datos (una vez)

```
cd guia-didactica-ra-ia\servidor\backend
python scripts\inicializar_db.py
```

Debe imprimir `Base de datos al día (alembic upgrade head).`. Si no ejecutas este paso, las tablas no existen y
fallan los endpoints de usuarios, chat, perfil e historial.

### 1.7 Arrancar

Desde `servidor/`:

```
iniciar_servidor.bat
```

o el equivalente a mano:

```
cd guia-didactica-ra-ia\servidor
set PYTHONPATH=backend
python -m uvicorn app.main:app --reload --port 8000 --app-dir backend
```

**El primer arranque tarda.** El índice vectorial (`servidor/base_vectorial/`) no está en el repositorio: al
arrancar, el servidor lo construye solo a partir de los 10 `.md` de `documentacion/markdown/`. Además descarga el
modelo de embeddings. Los arranques siguientes son rápidos.

**Si vas a probar con un teléfono físico** (no con el emulador), uvicorn tiene que escuchar en todas las
interfaces. Por defecto escucha solo en `127.0.0.1` y el teléfono no lo alcanza:

```
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --app-dir backend
```

Además, el Firewall de Windows tiene que permitir el puerto 8000 en la red privada. La app ya tiene
`android:usesCleartextTraffic="true"` en el `AndroidManifest.xml`, así que HTTP sin TLS funciona.

| Desde dónde llama la app | URL base |
|---|---|
| Emulador Android en el mismo PC | `http://10.0.2.2:8000` |
| Teléfono físico en la misma wifi | `http://<IPv4 del PC>:8000` (sale en `ipconfig`) y arrancar con `--host 0.0.0.0` |
| Flutter web / escritorio en el mismo PC | `http://127.0.0.1:8000` |

### 1.8 Comprobar que funciona

1. **Salud (sin token):**
   ```
   curl http://127.0.0.1:8000/api/v1/salud
   ```
   Respuesta esperada:
   ```json
   {"estado":"ok","modelo":"llama3.2","ollama_disponible":true,"documentos_indexados":10,"chunks_indexados":111}
   ```
   Si `estado` es `"degradado"`, Ollama no responde: revisa `ollama list`. Si `documentos_indexados` es `0`,
   el índice no se construyó: mira la consola del servidor.
2. **Documentación interactiva:** abre `http://127.0.0.1:8000/docs` (Swagger de FastAPI) para ver todas las rutas
   y sus esquemas.
3. **Una pregunta real con token** (opcional; comprueba también Firebase). Saca un `id_token` con la API REST de
   Firebase, usando la `apiKey` de la plataforma web de `lib/firebase_options.dart` y un usuario de correo y
   contraseña que ya exista en el proyecto:
   ```
   curl -X POST "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=<apiKey>" ^
        -H "Content-Type: application/json" ^
        -d "{\"email\":\"<correo>\",\"password\":\"<clave>\",\"returnSecureToken\":true}"
   ```
   Copia el campo `idToken` de la respuesta. Dura 1 hora. Después:
   ```
   curl -X POST http://127.0.0.1:8000/api/v1/usuarios/consentimiento -H "Authorization: Bearer <idToken>"
   curl -X POST http://127.0.0.1:8000/api/v1/chat -H "Authorization: Bearer <idToken>" ^
        -H "Content-Type: application/json" -d "{\"mensaje\":\"¿Qué es la ISO 9001?\"}"
   ```
   Si la segunda llamada devuelve un JSON con `"respuesta"`, el backend está listo. Si devuelve `401` con
   `"Token de Firebase inválido: RuntimeError: FIREBASE_CREDENTIALS_PATH no está configurado ..."`, el servidor no
   encontró el `.env` (revisa el recuadro de la sección 1.5).
4. **Pruebas automáticas** (opcional; no necesitan ni Ollama ni Firebase): desde `servidor/backend`, ejecuta
   `python -m pytest`.

---

## 2. Contrato de los endpoints que usa la app

Todas las rutas empiezan con `/api/v1`. Base en el emulador: `http://10.0.2.2:8000/api/v1`.

| Método y ruta | Token | Consentimiento | Para qué |
|---|---|---|---|
| `GET /salud` | no | no | ¿Está vivo el backend? ¿Responde Ollama? |
| `GET /cola/estado` | no | no | Estado en vivo de la cola de generación |
| `GET /usuarios/yo` | sí | no | Quién soy, mi rol y si acepté el consentimiento |
| `POST /usuarios/consentimiento` | sí | no | Aceptar el consentimiento informado |
| `POST /chat` | sí | **sí** | Preguntar al tutor |
| `GET /perfil/{uid}` | sí | no | Perfil adaptativo: nivel por unidad, dificultades… |
| `GET /perfil/{uid}/progreso` | sí | no | Evolución del nivel estimado por unidad |
| `POST /perfil/{uid}/reiniciar` | sí | no | Volver al perfil inicial |
| `GET /progreso/mio` | sí | no | XP, racha, lecciones y ejercicios |
| `POST /progreso/lecciones/{leccion_id}/completar` | sí | no | Registrar una lección completada |
| `POST /progreso/ejercicios/{ejercicio_id}/resolver` | sí | no | Registrar un ejercicio resuelto |
| `GET /historial/conversaciones` | sí | no | Mis conversaciones guardadas |
| `GET /historial/conversaciones/{id}/mensajes` | sí | no | Los mensajes de una conversación |

Todas las fechas van en ISO 8601 UTC (`2026-10-09T20:23:30+00:00`), salvo `ultima_actividad_fecha`, que es solo
la fecha (`2026-10-09`). Todos los errores tienen la forma `{"detail": "..."}`, excepto el 422, donde `detail` es
una lista.

### Flujo de arranque recomendado

1. El usuario inicia sesión con **Firebase Auth** en la app y obtienes el `id_token` (sección 3).
2. Llamas a `GET /salud`. Si falla la conexión o `estado != "ok"`, avisas de que el tutor no está disponible.
3. Llamas a `GET /usuarios/yo`. Si `consentimiento_aceptado == false`, muestras el consentimiento y, al aceptar,
   llamas a `POST /usuarios/consentimiento`.
4. Usas `POST /chat`. Guarda el `conversacion_id` que devuelve y reenvíalo en cada mensaje del mismo hilo.

---

### `GET /api/v1/salud`

Público. Archivo: `backend/app/api/v1/endpoints/salud.py`. No genera nada con el modelo: pregunta a Ollama si
está vivo, con un timeout de 2 s.

**Respuesta 200 (real):**
```json
{
  "estado": "ok",
  "modelo": "llama3.2",
  "ollama_disponible": true,
  "documentos_indexados": 10,
  "chunks_indexados": 111
}
```

| Campo | Tipo | Significado |
|---|---|---|
| `estado` | string | `"ok"` si Ollama responde; `"degradado"` si el servidor está arriba pero Ollama no |
| `modelo` | string | Valor de `MODELO_LLM`. No garantiza que el modelo esté descargado |
| `ollama_disponible` | bool | Resultado de la comprobación contra Ollama |
| `documentos_indexados` | int | Documentos en el índice (hoy, 10) |
| `chunks_indexados` | int | Fragmentos en el índice (hoy, 111) |

Siempre responde 200 mientras el proceso esté vivo. Si no lo está, verás un error de conexión en el cliente.

---

### `GET /api/v1/cola/estado`

Público. Archivo: `backend/app/api/v1/endpoints/chat.py` (`estado_cola`). Se explica en la sección 4.

**Respuesta 200 (real, servidor en reposo):**
```json
{"limite": 2, "generando": 0, "en_espera": 0, "tiempo_medio_generacion_s": 5.0, "espera_maxima_s": 120.0}
```

| Campo | Significado |
|---|---|
| `limite` | Cuántas respuestas se pueden generar a la vez (`LIMITE_GENERACIONES_SIMULTANEAS`) |
| `generando` | Cuántas se están generando ahora mismo |
| `en_espera` | Cuántas peticiones esperan turno ahora mismo, sumando las de todos los estudiantes |
| `tiempo_medio_generacion_s` | Media móvil de las últimas 20 generaciones reales. Al arrancar vale 5.0 |
| `espera_maxima_s` | A partir de esta espera, el servidor responde 503 |

---

### `GET /api/v1/usuarios/yo`

Archivo: `backend/app/api/v1/endpoints/usuarios.py`. La **primera** vez que el backend ve un uid, crea el usuario
con `rol: "estudiante"` y `consentimiento_aceptado: false`. No existe un endpoint de registro aparte.

**Respuesta 200 (real, usuario recién creado):**
```json
{
  "uid": "uid-ana-123",
  "correo": "ana.perez@upec.edu.ec",
  "nombre": "Ana Pérez",
  "foto_url": null,
  "proveedor": "password",
  "rol": "estudiante",
  "fecha_registro": "2026-10-09T20:23:30+00:00",
  "ultimo_acceso": "2026-10-09T20:23:30+00:00",
  "consentimiento_aceptado": false,
  "consentimiento_fecha": null
}
```

| Campo | Significado |
|---|---|
| `uid` | uid de Firebase. Es el que se usa en `/perfil/{uid}` |
| `correo`, `nombre`, `foto_url` | Lo que trae el token de Firebase. Se actualizan en cada llamada |
| `proveedor` | `"password"` o `"google"` |
| `rol` | `"estudiante"`, `"docente"` o `"admin"`. Solo se cambia a mano en la base de datos |
| `fecha_registro`, `ultimo_acceso` | Cuándo se creó el usuario y su última petición autenticada |
| `consentimiento_aceptado` | Si es `false`, `/chat` responde 409 |
| `consentimiento_fecha` | Cuándo aceptó, o `null` si no ha aceptado |

### `POST /api/v1/usuarios/consentimiento`

No lleva cuerpo. Responde con el mismo objeto que `/usuarios/yo`, ya con `"consentimiento_aceptado": true` y
`"consentimiento_fecha": "2026-10-09T20:23:30+00:00"`. Se puede llamar varias veces sin problema, pero cada
llamada actualiza la fecha.

---

### `POST /api/v1/chat`

Archivo: `backend/app/api/v1/endpoints/chat.py`. Exige token **y** consentimiento aceptado.

**Entrada:**
```json
{
  "mensaje": "¿Qué es la ISO 9001?",
  "conversacion_id": "1a9e1f9afdf24033ac509fd9ddb236dc",
  "leccion_id": "leccion-iso-9001"
}
```

| Campo | Tipo | Obligatorio | Significado |
|---|---|---|---|
| `mensaje` | string | **sí** | La pregunta del estudiante |
| `conversacion_id` | string, máx. 100 | no | Hilo de conversación. En el primer mensaje no lo envíes (o envíalo `null`): el servidor genera uno y lo devuelve. Reenvíalo después para que el tutor recuerde los turnos anteriores. Esa memoria vive en la RAM del servidor y se pierde si se reinicia |
| `leccion_id` | string, máx. 100 | no | Lección de la app en la que está el estudiante. Solo tiene efecto si existe en `configuracion/lecciones.json` (ver la nota al final de este apartado). Un id desconocido no produce error: se ignora |

**No existen** `message`, `normativa`, `system_context`, `capitulo_id` ni `norma_filtro`. Los campos que no
conoce se descartan sin error, y si falta `mensaje` la respuesta es 422 (ver abajo).

**Respuesta 200 (real; primera pregunta dentro de la lección de ISO 9001):**
```json
{
  "respuesta": "La certificación es otorgada por organismos de certificación acreditados, mediante auditorías externas periódicas. ¿Cómo se relaciona el ciclo PDCA con las diez cláusulas de la norma?",
  "tipo": "respuesta",
  "conversacion_id": "1a9e1f9afdf24033ac509fd9ddb236dc",
  "desde_cache": false,
  "latencia_ms": 10066.0,
  "tema_detectado": "ISO 9001: sistema de gestión de la calidad",
  "unidad_detectada": 2,
  "tema_id_detectado": "2.2",
  "metodo_deteccion": "leccion",
  "adaptacion": {
    "nivel": "medio",
    "profundidad": "media",
    "estilo": "conceptual",
    "dificultad": false,
    "segmento": "",
    "referencias": []
  },
  "posicion_en_cola": null,
  "espera_estimada_s": null,
  "espera_real_s": null
}
```

| Campo | Tipo | Significado y qué hacer en la app |
|---|---|---|
| `respuesta` | string | El texto del tutor, en Markdown ligero (listas con `*`, a veces `**negrita**`). Muéstralo con un widget que renderice Markdown o, como mínimo, respetando los saltos de línea |
| `tipo` | string | Qué clase de respuesta es (tabla siguiente) |
| `conversacion_id` | string | Guárdalo y reenvíalo en el siguiente mensaje del hilo |
| `desde_cache` | bool | `true` si salió del caché semántico sin llamar al modelo, en milisegundos |
| `latencia_ms` | number | Lo que tardó el servidor en **generar**. No incluye el tiempo en cola (sección 4) |
| `tema_detectado` | string \| null | Tema del sílabo al que pertenece la pregunta |
| `unidad_detectada` | int \| null | Unidad (1–4) |
| `tema_id_detectado` | string \| null | Id del tema en `configuracion/silabo.yaml` (por ejemplo, `"2.2"`) |
| `metodo_deteccion` | string \| null | Cómo se ubicó el tema: `palabras_clave`, `llm`, `embedding`, `leccion` o `seguimiento` |
| `adaptacion` | object \| null | Cómo se adaptó la respuesta al perfil. Es `null` en saludo, redirección y `sin_contexto` |
| `posicion_en_cola` | int \| null | Ver sección 4 |
| `espera_estimada_s` | number \| null | Ver sección 4 |
| `espera_real_s` | number \| null | Ver sección 4 |

**Valores de `tipo`** (todos con HTTP 200):

| `tipo` | Cuándo | Qué mostrar |
|---|---|---|
| `respuesta` | Respuesta normal desde los documentos | La respuesta |
| `saludo` | El mensaje es un saludo exacto ("hola") | La respuesta. Es instantánea: `latencia_ms` real fue 0.5 |
| `funcionamiento` | Preguntó qué puede hacer el tutor | La respuesta |
| `sin_contexto` | Pregunta del temario, pero sin documentación indexada (sección 7) | La respuesta. **No es un error** |
| `redireccion` | Pregunta fuera del temario | La respuesta (el tutor reconduce al curso) |
| `sin_documentos` | El índice está vacío (backend mal levantado) | Un aviso: es un problema del servidor |
| `error` | Excepción al generar (poco común). El texto del error viene en `respuesta` | Un mensaje de error y la opción de reintentar |

**`adaptacion`:**

| Campo | Valores | Significado |
|---|---|---|
| `nivel` | `bajo` / `medio` / `alto` | Franja estimada del estudiante en la unidad de la pregunta |
| `profundidad` | `breve` / `media` / `extensa` | Cuánto se extendió la explicación |
| `estilo` | `conceptual` / `ejemplos` / `comparativo` | Enfoque de la explicación |
| `dificultad` | bool | El tema está entre los que le han costado |
| `segmento` | string | Uso interno del caché. `""` significa que no hubo ajuste |
| `referencias` | lista de `{tema_id, tema, unidad}` | Temas ya trabajados en los que se apoyó la explicación |

Más ejemplos reales del mismo día:

- **Fuera del temario** (`"¿Cuál es la capital de Francia?"`): `"tipo": "redireccion"`, todos los campos de tema
  en `null`, `"adaptacion": null`, `"latencia_ms": 7043.6`.
- **Saludo** (`"hola"`): `"tipo": "saludo"`,
  `"respuesta": "¡Hola! Soy tu Tutor IA especializado en normativas de Ingeniería de Software. ¿Sobre qué norma o concepto te gustaría que te oriente hoy?"`,
  `"latencia_ms": 0.5`.
- **Tema sin documentación**: en la sección 7.
- **Respuesta adaptada.** Después de que el estudiante pidiera "No entiendo, ¿me lo explicas con un ejemplo?",
  repetir "¿Qué es la ISO 9001?" produjo
  `"adaptacion": {"nivel": "bajo", "profundidad": "media", "estilo": "conceptual", "dificultad": true, "segmento": "n=bajo|d=1", "referencias": []}`
  y una explicación con una analogía de un taller mecánico. Fíjate en que **no** salió del caché
  (`desde_cache: false`): el caché se separa por perfil, y una respuesta para un estudiante con dificultad no se
  reutiliza para uno sin ella.

**Errores de `/chat`:**

| Código | Cuándo | Cuerpo real |
|---|---|---|
| 401 | Falta el token o no es válido | Sección 3 |
| 409 | No ha aceptado el consentimiento | Sección 3 |
| 422 | Falta `mensaje`, o un id tiene más de 100 caracteres | Abajo |
| 503 | Más de `ESPERA_MAXIMA_COLA_S` (120 s) esperando turno | `{"detail": "El tutor está saturado: más de 120 s esperando turno (posición al llegar: N). Intenta de nuevo en un momento."}` |

422 real, al enviar el formato antiguo `{"message": "hola", "normativa": "ISO 9001"}`:
```json
{"detail": [{"type": "missing", "loc": ["body", "mensaje"], "msg": "Field required",
             "input": {"message": "hola", "normativa": "ISO 9001"}}]}
```

**Nota sobre `leccion_id`.** Hoy `configuracion/lecciones.json` solo conoce estos ids: `leccion-metodologias-agiles`
(→ tema 1.2), `leccion-iso-9001` (→ 2.2), `leccion-iso-25010` (→ 2.5), `leccion-metricas-agiles` (→ 3.4) y
`leccion-pruebas-software` (→ 4.1). Los ids reales de la app (`cap-1-1-lec-1`, `cap-2-2-lec-1`…, en
`lib/data/mock_data_silabo.dart`) **no están en ese archivo**. Puedes enviarlos igualmente, porque no rompen nada,
pero no tendrán efecto hasta que se añada al JSON una línea `"cap-2-2-lec-1": "2.2"` por lección. Pásale a
Sebastián la tabla *id de la lección → tema del sílabo* y él la añade, o añádela tú con un PR: es solo ese JSON.

---

### `GET /api/v1/perfil/{uid}`

Archivo: `backend/app/api/v1/endpoints/perfil.py`. `{uid}` es el `uid` de `/usuarios/yo`, que es el mismo uid de
Firebase (`FirebaseAuth.instance.currentUser!.uid`). Un estudiante solo puede pedir **el suyo**:

```json
{"detail": "No puedes acceder al perfil de otro estudiante."}
```
(403 real, al pedir `/perfil/otro-uid`.)

**Respuesta 200 (real, después de 6 mensajes de chat):**
```json
{
  "user_id": "uid-ana-123",
  "nivel_por_unidad": {"1": 3.0, "2": 2.6, "3": 3.0, "4": 3.0},
  "temas_consultados": {"2.2": 3, "3.5": 1},
  "temas_con_dificultad": ["2.2"],
  "profundidad_preferida": "media",
  "estilo_preferido": "conceptual",
  "ritmo": {"sesiones": 5, "mensajes_totales": 6, "mensajes_por_sesion": 1.2, "duracion_media_s": 8.0},
  "historial_resumido": [
    {"tema_id": "3.5", "tema": "Métricas DORA de DevOps", "unidad": 3, "fecha": "2026-10-09T20:23:52+00:00"},
    {"tema_id": "2.2", "tema": "ISO 9001: sistema de gestión de la calidad", "unidad": 2, "fecha": "2026-10-09T20:24:05+00:00"}
  ],
  "aclaraciones_por_tema": {"2.2": 1},
  "senales_recientes": ["ejemplo"],
  "creado_en": "2026-10-09T20:23:41+00:00",
  "actualizado_en": "2026-10-09T20:24:05+00:00",
  "es_nuevo": false,
  "resumen_historial": "«ISO 9001: sistema de gestión de la calidad» (Unidad 2); «Métricas DORA de DevOps» (Unidad 3)",
  "dificultades": [{"tema_id": "2.2", "tema": "ISO 9001: sistema de gestión de la calidad", "unidad": 2}]
}
```

| Campo | Significado |
|---|---|
| `nivel_por_unidad` | Nivel estimado de 1.0 a 5.0 por unidad; el inicial es 3.0. **Las claves son strings** (`"1"`…`"4"`). Por debajo de 2.5 se considera "bajo" y por encima de 3.5, "alto" |
| `temas_consultados` | Id de tema → cuántas veces preguntó por él |
| `temas_con_dificultad` | Ids de los temas que le cuestan. Para mostrarlos usa `dificultades`, que trae los nombres |
| `profundidad_preferida`, `estilo_preferido` | Lo que el tutor ha inferido de cómo pregunta |
| `ritmo` | `sesiones` = conversaciones distintas; `duracion_media_s` cuenta solo las conversaciones de 2 o más mensajes |
| `historial_resumido` | Últimos 5 temas distintos, **el más reciente al final** |
| `aclaraciones_por_tema`, `senales_recientes` | Estado interno de la inferencia. La app puede ignorarlos |
| `creado_en`, `actualizado_en` | `null` mientras no exista un perfil guardado |
| `es_nuevo` | `true` = todavía no ha chateado: es el perfil inicial (niveles en 3.0 y listas vacías) |
| `resumen_historial` | Los últimos temas en una línea, el más reciente primero. Se puede mostrar tal cual |
| `dificultades` | `temas_con_dificultad` con nombre y unidad |

Un estudiante que todavía no ha chateado recibe 200 con `"es_nuevo": true`, niveles en 3.0, listas vacías y
`creado_en: null`. Esa consulta no crea nada.

### `GET /api/v1/perfil/{uid}/progreso`

Evolución del nivel estimado, pensada para dibujar una gráfica por unidad. Respuesta real, recortada a 2 de las 4
unidades:

```json
{
  "user_id": "uid-ana-123",
  "unidades": [
    {"unidad": 1, "titulo": "Aplicación de metodología de desarrollo de software", "nivel_actual": 3.0,
     "puntos": [{"fecha": "2026-10-09T20:23:41+00:00", "nivel": 3.0, "motivo": "inicial", "tema_id": null}]},
    {"unidad": 2, "titulo": "Normativas de desarrollo y calidad del software", "nivel_actual": 2.6,
     "puntos": [{"fecha": "2026-10-09T20:23:41+00:00", "nivel": 3.0, "motivo": "inicial", "tema_id": null},
                {"fecha": "2026-10-09T20:23:49+00:00", "nivel": 2.6, "motivo": "confusion", "tema_id": "2.2"}]}
  ]
}
```

Siempre llegan las 4 unidades, en orden. Los títulos de las unidades 3 y 4 son "Métricas de gestión de proyectos
de software" y "Gestión de pruebas, implementación y mantenimiento". `motivo` vale `inicial`, `confusion` o
`reflexion_correcta`. En un estudiante nuevo, `fecha` del punto inicial puede ser `null`.

### `POST /api/v1/perfil/{uid}/reiniciar`

No lleva cuerpo. Borra el perfil adaptativo, pero **no** el historial de conversaciones. Responde como
`GET /perfil/{uid}`, con `es_nuevo: true`.

---

### `GET /api/v1/progreso/mio`

Archivo: `backend/app/api/v1/endpoints/progreso.py`. Es la gamificación de la app: XP, racha, lecciones y
ejercicios. Usa siempre el estudiante del token y **no** recibe ningún uid. Hoy la app guarda esto solo en memoria
(`lib/services/progreso_service.dart`); este endpoint lo hace persistente.

**Respuesta 200 (real, estudiante sin actividad):**
```json
{"xp_total": 0, "racha_actual": 0, "racha_mejor": 0, "ultima_actividad_fecha": null,
 "lecciones_completadas": 0, "ejercicios_resueltos": 0, "ejercicios_correctos": 0}
```

### `POST /api/v1/progreso/lecciones/{leccion_id}/completar`

No lleva cuerpo. `leccion_id` es libre: usa directamente el id de la app, por ejemplo `cap-2-2-lec-1`. Respuesta
real, con el mismo formato que `/progreso/mio`:
```json
{"xp_total": 20, "racha_actual": 1, "racha_mejor": 1, "ultima_actividad_fecha": "2026-10-09",
 "lecciones_completadas": 1, "ejercicios_resueltos": 0, "ejercicios_correctos": 0}
```

### `POST /api/v1/progreso/ejercicios/{ejercicio_id}/resolver`

**Entrada:**
```json
{"correcto": true, "leccion_id": "leccion-iso-9001"}
```
`correcto` (bool) es obligatorio. `leccion_id` es opcional y solo informativo. Respuesta real:
```json
{"xp_total": 30, "racha_actual": 1, "racha_mejor": 1, "ultima_actividad_fecha": "2026-10-09",
 "lecciones_completadas": 1, "ejercicios_resueltos": 1, "ejercicios_correctos": 1}
```

**Reglas** (`backend/app/services/progreso_service.py`):

- XP: una lección da +20, un ejercicio correcto +10 y uno incorrecto +2.
- Racha: el primer evento de un día que sigue al anterior suma 1. Varios eventos el mismo día no la suben más. Un
  hueco de más de un día la vuelve a 1.
- Completar dos veces la misma lección **suma XP dos veces**: el backend no deduplica. Si la app no debe permitirlo,
  controla tú que solo se llame una vez.

---

### `GET /api/v1/historial/conversaciones`

Archivo: `backend/app/api/v1/endpoints/historial.py`. Devuelve las conversaciones del estudiante del token, la
más reciente primero. A diferencia de la memoria del chat, que vive en RAM, el historial está guardado en la base
de datos.

**Respuesta 200 (real, recortada a 2 de 5):**
```json
[
  {"id": "78844a041b6b4fdea76e51455793ba47", "titulo": "¿Qué es la ISO 9001?",
   "fecha_inicio": "2026-10-09T20:24:05+00:00", "fecha_ultimo_mensaje": "2026-10-09T20:24:05+00:00"},
  {"id": "1a9e1f9afdf24033ac509fd9ddb236dc", "titulo": "¿Qué es la ISO 9001?",
   "fecha_inicio": "2026-10-09T20:23:41+00:00", "fecha_ultimo_mensaje": "2026-10-09T20:23:49+00:00"}
]
```
`id` es el mismo `conversacion_id` de `/chat`. `titulo` es el primer mensaje del estudiante y puede ser `null`.

### `GET /api/v1/historial/conversaciones/{id}/mensajes`

**Respuesta 200 (real, recortada):**
```json
[
  {"rol": "estudiante", "contenido": "¿Qué es la ISO 9001?", "tipo": null, "fecha": "2026-10-09T20:23:41+00:00"},
  {"rol": "tutor", "contenido": "La certificación es otorgada por organismos de certificación acreditados, ...",
   "tipo": "respuesta", "fecha": "2026-10-09T20:23:41+00:00"},
  {"rol": "estudiante", "contenido": "No entiendo, ¿me lo explicas con un ejemplo?", "tipo": null,
   "fecha": "2026-10-09T20:23:49+00:00"}
]
```

- `rol`: `"estudiante"` o `"tutor"`.
- `tipo`: el mismo `tipo` de `/chat` en los mensajes del tutor, y `null` en los del estudiante.
- Si la conversación no existe o es de otro estudiante, responde 404 con `{"detail": "Conversación no encontrada."}`.
  Las dos situaciones dan la misma respuesta a propósito.

Para **continuar** una conversación antigua, envía su `id` como `conversacion_id` en `/chat`. Si el servidor se
reinició desde entonces, el tutor no recordará los turnos anteriores (esa memoria vive en RAM), aunque el historial
siga mostrándolos.

---

## 3. Autenticación

### Qué cabecera

```
Authorization: Bearer <id_token de Firebase>
```

Código: `backend/app/api/deps.py`. El `id_token` es el que entrega el SDK de Firebase Auth después de iniciar
sesión. En Flutter:

```dart
final token = await FirebaseAuth.instance.currentUser!.getIdToken();
```

El SDK lo renueva solo; caduca a la hora. Pídelo justo antes de cada petición, en lugar de guardarlo al iniciar
sesión.

> **Importante para la app actual:** `lib/services/auth_service.dart` hoy **no** usa Firebase Auth. Con
> `AuthConfig.usarServidor = false` guarda los usuarios en el dispositivo, y `AuthRemoto` llama a
> `/auth/registro` y `/auth/login`, **que no existen en este backend**. Sin un usuario de Firebase no hay
> `id_token`, y sin `id_token` todos los endpoints protegidos responden 401. El registro y el inicio de sesión
> tienen que pasar a `FirebaseAuth.instance.createUserWithEmailAndPassword` y
> `FirebaseAuth.instance.signInWithEmailAndPassword` (o Google Sign-In). `firebase_auth` ya está en `pubspec.yaml`
> y `Firebase.initializeApp` ya se llama en `main.dart`. El backend crea al usuario solo la primera vez que recibe
> su token, así que no hay que llamar a ningún endpoint de registro.

### Qué pasa si falta el token

Respuesta 401 real, tanto si falta la cabecera como si no empieza por `Bearer `:
```json
{"detail": "Falta el encabezado Authorization: Bearer <id_token>."}
```

Si el token está caducado, mal firmado o es de otro proyecto de Firebase, también es 401:
```json
{"detail": "Token de Firebase inválido: <TipoDeError>: <mensaje de Firebase>"}
```

Qué hacer en la app ante un 401: renovar el token con `getIdToken(true)` y reintentar **una vez**. Si vuelve a
fallar, enviar al usuario al inicio de sesión.

Si el **servidor** no tiene configurado `FIREBASE_CREDENTIALS_PATH`, cualquier endpoint protegido responde
**también 401**, pero con
`"detail": "Token de Firebase inválido: RuntimeError: FIREBASE_CREDENTIALS_PATH no está configurado ..."`. Si ves
ese texto, renovar el token no sirve de nada: el problema es del backend, no de la app (sección 1.5).

### Qué pasa si falta el consentimiento

Solo afecta a `POST /chat`. Respuesta 409 real:
```json
{"detail": "Falta aceptar el consentimiento informado antes de usar el tutor. Acéptalo primero con POST /api/v1/usuarios/consentimiento."}
```

Qué hacer en la app: mostrar la pantalla de consentimiento y, si el usuario acepta, llamar a
`POST /api/v1/usuarios/consentimiento` y reenviar la pregunta. Para no llegar nunca al 409, consulta
`GET /usuarios/yo` al iniciar sesión (flujo de la sección 2).

### Otros 403

- `GET /perfil/{uid}` con un uid que no es el tuyo: `{"detail": "No puedes acceder al perfil de otro estudiante."}`.
- Los endpoints de docente o admin, que la app de estudiante no usa: `{"detail": "Se requiere el rol docente o admin."}`.

---

## 4. Los campos de cola

### Por qué existe la cola

Un solo Ollama en una sola GPU no genera más rápido dos respuestas a la vez: las hace más lentas a las dos. Por
eso el backend deja generar a la vez solo `LIMITE_GENERACIONES_SIMULTANEAS` respuestas (2 por defecto) y el resto
**espera su turno** (`backend/app/services/cola_service.py`). Los aciertos de caché y los saludos no pasan por la
cola.

### Qué campos y cuándo aparecen

Están en la respuesta de `POST /chat`:

| Campo | `null` cuando… | Si tiene valor |
|---|---|---|
| `posicion_en_cola` | La petición no esperó: había un cupo libre, o la respuesta salió del caché o fue un saludo | Cuántas peticiones esperaban **delante** al llegar. `0` significa que no había nadie esperando, pero los dos cupos estaban ocupados y tuvo que esperar a que se liberara uno |
| `espera_estimada_s` | Igual que el anterior | Estimación hecha al llegar: `posicion × tiempo_medio_generacion_s` |
| `espera_real_s` | Igual que el anterior | Segundos que esperó realmente hasta conseguir un cupo |

Ejemplo real: 5 preguntas distintas lanzadas a la vez el 2026-10-09 con el límite en 2.

| Pregunta | `posicion_en_cola` | `espera_estimada_s` | `espera_real_s` | `latencia_ms` |
|---|---|---|---|---|
| ¿Qué fases tiene el ciclo de vida…? | `null` | `null` | `null` | 3099.1 |
| ¿Qué es ISO/IEC 29110? | `null` | `null` | `null` | 7923.3 |
| ¿Qué es la gestión del riesgo…? | `0` | `0.0` | `3.11` | 3511.4 |
| ¿Qué es un SGSI…? | `1` | `5.55` | `6.62` | 3669.0 |
| ¿Qué niveles de capacidad…? | `2` | `11.1` | `7.89` | 3738.6 |

Lo que tarda en total una petición es aproximadamente `espera_real_s + latencia_ms/1000`. **`latencia_ms` no
incluye la espera en cola.**

### La trampa: los campos llegan al final

Estos tres campos llegan **con la respuesta**, es decir, cuando la espera ya terminó. Mientras la petición está
pendiente, la app no recibe nada de esa petición. Para mostrar algo útil durante la espera:

1. **Mientras esperas la respuesta**, si pasan más de unos 3 s sin respuesta, consulta
   `GET /api/v1/cola/estado` (público y barato) cada 3 s hasta que llegue:
   - Si `en_espera > 0`, muestra algo como *"El tutor está atendiendo a otros estudiantes (N en espera, unos
     N × tiempo_medio_generacion_s segundos)"*.
   - Si `en_espera == 0`, muestra simplemente *"El tutor está escribiendo…"*.

   `en_espera` es el total del servidor, no tu posición exacta: trátalo como una estimación.
2. **Cuando llega la respuesta**, si `espera_real_s` no es `null` y es mayor que unos 5 s, puedes poner una nota
   discreta bajo la burbuja, por ejemplo *"Esperaste 38 s en cola"*. Así el estudiante entiende por qué tardó.
3. **Si llega un 503** (más de 120 s en cola), muestra *"El tutor está saturado, inténtalo en un momento"* con un
   botón de reintentar. No reintentes automáticamente: solo alargaría la cola.

### Datos reales de `reportes/prueba_concurrencia.md`

La prueba se hizo el 2026-09-29 contra el modelo real, con N peticiones **exactamente a la vez**, límite 2 y una
espera máxima de 90 s en esa prueba (hoy el valor por defecto es 120 s):

| Peticiones simultáneas | Errores | Duración total | Latencia del servidor (media / p95) | Esperaron cupo | Posición máx. | Espera media / máx. de las que esperaron |
|---|---|---|---|---|---|---|
| 10 | 0 | 30,15 s | 5,73 s / 8,17 s | 8 de 10 | 7 | 15,16 s / 23,74 s |
| 20 | 0 | 50,29 s | 5,01 s / 9,64 s | 14 de 20 | 13 | 22,00 s / 43,77 s |
| 40 | 0 | 78,48 s | 3,93 s / 10,71 s | 30 de 40 | 29 | 38,67 s / **72,64 s** |

Lo que significa para la app:

- Con una clase entera preguntando a la vez, **la mayoría de las peticiones esperan**, y la última de 40 esperó
  **más de un minuto** antes de empezar a generar. Si la app solo muestra un indicador de carga genérico durante
  70 s, el estudiante pensará que se ha colgado. Por eso hay que mostrar el estado de la cola.
- La generación en sí no se degrada con la carga: la mediana se mantiene entre 3,7 y 6,6 s. Lo que crece es la
  espera.
- Con 40 peticiones, la espera máxima (72,6 s) se acercó al tope. Con más carga empezarían a aparecer 503, así
  que la app tiene que tratarlos (punto 3 de arriba).
- Ese reporte habla de "el campo `cola`". Es un nombre antiguo: los campos reales son los tres de esta sección.

---

## 5. Latencias y timeouts

### Qué esperar

Los datos de `reportes/comparativa_modelos.md` se midieron con el modelo real en un portátil con una **RTX 3060 de
6 GB** y 16 GB de RAM.

| Modelo | Latencia media (banco de 18 preguntas) | Latencia (banco de adaptación) |
|---|---|---|
| **llama3.2** (el que se usa) | **2,4 s** (mediana 1,9 s; p95 6,6 s) | **3,6 s** (de 1,7 a 8,1 s) |
| llama3.1:8b | 11,0 s (p95 20,3 s) | 22,6 s (de 12,5 a 40,2 s) |
| qwen2.5:7b-instruct | 16,6 s (p95 36,5 s) | 24,6 s (de 12,5 a 46,1 s) |
| mistral:7b | 10,3 s (p95 22,5 s) | 30,3 s (de 4,5 a **138,3 s**) |

Por eso el backend usa `llama3.2`: los modelos mayores son entre 4 y 7 veces más lentos y no respondieron mejor.
No cambies `MODELO_LLM`.

Lo que se midió el 2026-10-09 en las capturas de este documento:

| Caso | `latencia_ms` |
|---|---|
| Saludo | 0,5 ms |
| Tema sin documentación (`sin_contexto`) | ~2 s |
| Respuesta normal | 3,1 – 10,1 s |
| Redirección (fuera de tema) | ~7 s |
| Con 40 peticiones simultáneas (prueba de concurrencia) | p95 10,7 s, máx. 14,2 s, **más hasta 72,6 s en cola** |

Según los comentarios de `cola_service.py`, un acierto de caché responde en unos 20 ms; esto no se midió aquí.

En un PC **sin GPU NVIDIA** el modelo corre en la CPU y será bastante más lento. No está medido, así que no hay
números. La primera pregunta después de arrancar Ollama también tarda más, porque tiene que cargar el modelo en
memoria.

### Qué timeout configurar

| Petición | Timeout del cliente | Por qué |
|---|---|---|
| `POST /chat` | **150 s** | Hasta 120 s esperando en cola (`ESPERA_MAXIMA_COLA_S`) más unos 15 s de generación en el peor caso medido, más margen. Con menos, la app corta antes de recibir la respuesta o el 503 que explica la saturación. **Los 120 s que tiene ahora `chat_service.dart` se quedan cortos** |
| `GET /salud` | 5 s | El servidor espera como mucho 2 s a Ollama |
| `GET /cola/estado` | 5 s | Es instantáneo |
| Resto (`/usuarios`, `/perfil`, `/progreso`, `/historial`) | 15 s | Solo consultan la base de datos; responden en milisegundos |

---

## 6. Qué cambiar en `lib/services/chat_service.dart`

### Lo que hay hoy

Revisado en `origin/main` de `V-Erik/normativas_app`, commit `95e5c5d`:

```dart
static const String _baseUrl = 'http://10.25.233.4:8000/api/v1/chat';
...
headers: {'Content-Type': 'application/json'},
body: jsonEncode({
  'message': texto,
  'system_context': systemContext,
  'capitulo_id': capituloFiltro,
  'norma_filtro': normaFiltro,
}),
...
.timeout(const Duration(seconds: 120));
...
return data['response'] ?? 'El tutor se quedó sin palabras.';
```

Si tu copia local es otra versión, por ejemplo `http://10.0.2.2:5000/api/chat` con `{message, normativa}`, el
problema es el mismo: **ni el puerto 5000, ni la ruta `/api/chat`, ni los campos `message` o `normativa` existen en
este backend**.

Qué falla y por qué:

| Hoy | Problema | Correcto |
|---|---|---|
| IP fija `10.25.233.4` (o `10.0.2.2:5000`) | Una IP de una red concreta; 5000 no es el puerto | URL base configurable: `http://10.0.2.2:8000` en el emulador (sección 1.7) |
| Ruta `/api/v1/chat` (o `/api/chat`) | `/api/chat` no existe; `/api/v1/chat` es correcta | `POST /api/v1/chat` |
| Sin `Authorization` | **401** siempre | `Authorization: Bearer <id_token>` |
| `message` | **422**: falta `mensaje` | `mensaje` |
| `system_context` | Se ignora: el tutor tiene su propio prompt y **no** acepta instrucciones del cliente | Quitarlo (ver abajo el marcador `[[NIVEL_COMPLETADO]]`) |
| `capitulo_id`, `norma_filtro`, `normativa` | Se ignoran | `leccion_id` (el id de la lección) |
| No se guarda `conversacion_id` | Cada mensaje empieza una conversación nueva y el tutor no recuerda nada | Guardar el `conversacion_id` de la respuesta y reenviarlo |
| Lee `data['response']` | Ese campo no existe: siempre saldría "El tutor se quedó sin palabras." | `data['respuesta']` |
| Timeout de 120 s | Corta antes del 503 de cola | 150 s |
| Cualquier código ≠ 200 da el mismo mensaje | El estudiante no sabe si tiene que iniciar sesión, aceptar el consentimiento o esperar | Tratar 401, 409 y 503 por separado (sección 3) |

### Qué poner en su lugar

Sustituye el archivo completo por esto. Usa `firebase_auth` y `http`, que ya están en `pubspec.yaml`.

```dart
import 'dart:async';
import 'dart:convert';

import 'package:firebase_auth/firebase_auth.dart';
import 'package:http/http.dart' as http;

/// URL base del backend (servidor/ de guia-didactica-ra-ia).
/// Emulador Android: http://10.0.2.2:8000 · Teléfono físico: http://<IPv4 del PC>:8000
/// Se puede cambiar sin tocar el código: flutter run --dart-define=API_BASE=http://192.168.1.50:8000
const String apiBase = String.fromEnvironment('API_BASE', defaultValue: 'http://10.0.2.2:8000');

/// Respuesta de POST /api/v1/chat (ver servidor/docs/ENTREGA_FRONTEND.md, sección 2).
class RespuestaTutor {
  final String respuesta;
  final String tipo; // respuesta | saludo | funcionamiento | sin_contexto | redireccion | sin_documentos | error
  final String conversacionId;
  final bool desdeCache;
  final double latenciaMs;
  final String? temaDetectado;
  final int? unidadDetectada;
  final int? posicionEnCola;
  final double? esperaEstimadaS;
  final double? esperaRealS;

  RespuestaTutor.fromJson(Map<String, dynamic> j)
      : respuesta = j['respuesta'] as String,
        tipo = j['tipo'] as String,
        conversacionId = j['conversacion_id'] as String,
        desdeCache = j['desde_cache'] as bool,
        latenciaMs = (j['latencia_ms'] as num).toDouble(),
        temaDetectado = j['tema_detectado'] as String?,
        unidadDetectada = j['unidad_detectada'] as int?,
        posicionEnCola = j['posicion_en_cola'] as int?,
        esperaEstimadaS = (j['espera_estimada_s'] as num?)?.toDouble(),
        esperaRealS = (j['espera_real_s'] as num?)?.toDouble();
}

/// Error con un mensaje listo para mostrar y el código HTTP, para que la pantalla decida qué hacer
/// (401 → volver a iniciar sesión, 409 → mostrar el consentimiento, 503 → botón de reintentar).
class ErrorTutor implements Exception {
  final int? codigo;
  final String mensaje;
  ErrorTutor(this.codigo, this.mensaje);
  @override
  String toString() => mensaje;
}

class ChatService {
  static const _timeoutChat = Duration(seconds: 150);

  /// Envía [mensaje] al tutor. Pasa el [conversacionId] de la respuesta anterior para seguir el mismo hilo
  /// (null en el primer mensaje) y el [leccionId] si el estudiante está dentro de una lección.
  /// [alCambiarCola] recibe cada 3 s el estado de GET /cola/estado mientras se espera la respuesta.
  static Future<RespuestaTutor> preguntarAlTutor(
    String mensaje, {
    String? conversacionId,
    String? leccionId,
    void Function(Map<String, dynamic> estadoCola)? alCambiarCola,
  }) async {
    Timer? sondeo;
    if (alCambiarCola != null) {
      sondeo = Timer.periodic(const Duration(seconds: 3), (_) async {
        try {
          final r = await http.get(Uri.parse('$apiBase/api/v1/cola/estado')).timeout(const Duration(seconds: 5));
          if (r.statusCode == 200) alCambiarCola(jsonDecode(r.body) as Map<String, dynamic>);
        } catch (_) {/* el sondeo es informativo: si falla, no se interrumpe el chat */}
      });
    }
    try {
      var r = await _post(mensaje, conversacionId, leccionId, forzarToken: false);
      if (r.statusCode == 401) {
        r = await _post(mensaje, conversacionId, leccionId, forzarToken: true); // token caducado: un reintento
      }
      final cuerpo = jsonDecode(utf8.decode(r.bodyBytes));
      switch (r.statusCode) {
        case 200:
          return RespuestaTutor.fromJson(cuerpo as Map<String, dynamic>);
        case 401:
          throw ErrorTutor(401, 'Tu sesión expiró. Vuelve a iniciar sesión.');
        case 409:
          throw ErrorTutor(409, 'Antes de usar el tutor tienes que aceptar el consentimiento informado.');
        case 503:
          throw ErrorTutor(503, 'El tutor está atendiendo a muchos estudiantes. Inténtalo en un momento.');
        default:
          throw ErrorTutor(r.statusCode, 'Error del servidor (${r.statusCode}): ${cuerpo['detail']}');
      }
    } on TimeoutException {
      throw ErrorTutor(null, 'El tutor tardó demasiado en responder. Inténtalo de nuevo.');
    } on ErrorTutor {
      rethrow;
    } catch (_) {
      throw ErrorTutor(null, 'No se pudo conectar con el tutor. ¿Está encendido el servidor?');
    } finally {
      sondeo?.cancel();
    }
  }

  static Future<http.Response> _post(String mensaje, String? conversacionId, String? leccionId,
      {required bool forzarToken}) async {
    final usuario = FirebaseAuth.instance.currentUser;
    if (usuario == null) throw ErrorTutor(401, 'Inicia sesión para usar el tutor.');
    final token = await usuario.getIdToken(forzarToken);
    return http
        .post(
          Uri.parse('$apiBase/api/v1/chat'),
          headers: {'Content-Type': 'application/json', 'Authorization': 'Bearer $token'},
          body: jsonEncode({
            'mensaje': mensaje,
            if (conversacionId != null) 'conversacion_id': conversacionId,
            if (leccionId != null) 'leccion_id': leccionId,
          }),
        )
        .timeout(_timeoutChat);
  }
}
```

### Cambios en quien lo llama

**`lib/screens/chat_screen.dart`, en `sendMessage`:**

- Añade a la clase `String? _conversacionId;` y, si quieres mostrar la cola, `String? _estadoCola;`.
- Sustituye la llamada actual por:
  ```dart
  try {
    final r = await ChatService.preguntarAlTutor(
      mensaje,
      conversacionId: _conversacionId,
      leccionId: _esModoRuta ? widget.leccion?.id : null,
      alCambiarCola: (c) => setState(() => _estadoCola = (c['en_espera'] as int) > 0
          ? 'El tutor está atendiendo a otros estudiantes (${c['en_espera']} en espera)…'
          : null),
    );
    _conversacionId = r.conversacionId;
    // r.respuesta es el texto; r.esperaRealS != null → puedes mostrar "Esperaste X s en cola"
  } on ErrorTutor catch (e) {
    // e.codigo == 409 → abrir el consentimiento; 401 → ir al inicio de sesión; si no, mostrar e.mensaje
  }
  ```
- **El marcador `[[NIVEL_COMPLETADO]]` no va a llegar nunca.** Hoy la pantalla envía en `system_context` un prompt
  oculto que le pide al modelo escribir ese marcador cuando el estudiante acierta, y detecta la lección completada
  buscándolo en la respuesta. El backend descarta `system_context`: el tutor tiene su propio prompt pedagógico,
  que el cliente no puede sustituir. Así que la lección nunca se marcaría como completada. Decide tú en la app
  cuándo se completa una lección (botón "Terminar lección", ejercicios resueltos…) y entonces llama a
  `POST /api/v1/progreso/lecciones/{leccion.id}/completar`, que además guarda el XP y la racha en el servidor.
- El "arranque silencioso" de la lección en Modo Ruta (enviar un mensaje sin burbuja de usuario) sigue
  funcionando, pero solo con el texto visible de la pregunta, sin instrucciones ocultas.

**`lib/screens/ar_scanner_screen.dart`, línea ~98:** sigue funcionando con la nueva firma (solo el mensaje), pero
ahora devuelve `RespuestaTutor`. Usa `.respuesta` y envuelve la llamada en `try/on ErrorTutor`.

**`lib/services/auth_service.dart`:** pasa el inicio de sesión a Firebase Auth (sección 3). Sin eso, nada de lo
anterior funciona.

---

## 7. Los 9 temas del sílabo sin documentación

El tutor responde **solo** a partir de los 10 documentos indexados: ISO 9001, ISO/IEC 12207, 20000, 25010, 27001,
27002, 29110, 33000, ISO 31000 e ISO/IEC/IEEE 42010. Según `reportes/cobertura_silabo.md`, **9 de los 27 temas del
sílabo no aparecen en ningún documento**. El índice actual es el mismo que se auditó: 10 documentos y 111
fragmentos.

| Id | Tema | Unidad |
|---|---|---|
| 1.3 | Kanban (tablero, flujo de trabajo y límites de WIP) | 1 |
| 1.4 | Lean (eliminación de desperdicio y flujo de valor) | 1 |
| 2.7 | ISO/IEC 42001 y gobierno de la inteligencia artificial | 2 |
| 3.1 | Fundamentos de medición: KPIs, líneas base y GQM | 3 |
| 3.4 | Métricas ágiles y de flujo: lead time, cycle time, WIP y diagrama de flujo acumulado | 3 |
| 3.5 | Métricas DORA de DevOps | 3 |
| 3.6 | Métricas de experiencia de usuario, seguridad y sostenibilidad; tableros | 3 |
| 4.2 | TDD, automatización de pruebas, análisis estático y quality gates | 4 |
| 4.4 | Mantenimiento y evolución del software: ISO/IEC/IEEE 14764, refactorización y deuda técnica | 4 |

**Que el tutor diga que no tiene documentación sobre estos temas es el comportamiento correcto, no un fallo.** Está
hecho así a propósito para que no invente: sin documentos, un modelo pequeño se inventa la norma y la atribuye a
otra. Normalmente lo verás como `"tipo": "sin_contexto"` (HTTP 200), con el tema bien detectado. Ejemplo real:

```json
{
  "respuesta": "Parece que DORA no aparece en los documentos de la base que tenemos aquí. En cambio, sí hay un documento que trata sobre DevOps, específicamente sobre las métricas DORA de DevOps. ...",
  "tipo": "sin_contexto",
  "tema_detectado": "Métricas DORA de DevOps",
  "unidad_detectada": 3,
  "tema_id_detectado": "3.5",
  "adaptacion": null,
  "latencia_ms": 1988.9
}
```

En algunos casos llega como `"tipo": "respuesta"`, pero con un aviso de que hay poco material.

Qué sí es un fallo y conviene reportar: que el tutor **explique con seguridad** uno de estos temas como si viniera
de los documentos, o que **afirme que existe** un documento que no existe. El propio ejemplo de arriba lo hace en
su segunda frase ("sí hay un documento que trata sobre... las métricas DORA"): ese documento no existe. Cuando veas
algo así, anota el `conversacion_id`, la pregunta y la respuesta, y pásaselo a Sebastián.

Hay otros 12 temas con cobertura **parcial**: se mencionan en algún documento, pero ninguno los trata a fondo. La
lista está en `reportes/cobertura_silabo.md`. Ahí el tutor da lo poco que hay y debería decir que el resto no está
en los documentos. Lo mismo vale para la lección `leccion-metricas-agiles`, que apunta al tema 3.4, uno de los 9
de la tabla: dentro de esa lección el tutor no tendrá material.
