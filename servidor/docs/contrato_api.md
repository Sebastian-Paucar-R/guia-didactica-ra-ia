# Contrato de la API — Tutor IA (backend para la app Flutter)

Base URL en desarrollo: `http://127.0.0.1:8000` (emulador Android: `http://10.0.2.2:8000`). Todas las rutas
cuelgan de `/api/v1`, salvo `GET /` (página de prueba HTML) y `GET /documentacion/...` (archivos).

No se encontró un repositorio `normativas-app-upec` ni su README en esta máquina; este contrato se escribió a
partir del encargo (campos de `/chat`, progreso, salud, CORS, Postman) y del backend tal como está implementado.
Si el proyecto Flutter real usa otros nombres de campo, este es el documento a cambiar primero.

## Autenticación

Todas las rutas salvo `GET /api/v1/salud` y `GET /api/v1/cola/estado` exigen el header:

```
Authorization: Bearer <id_token>
```

`<id_token>` es un ID token de Firebase Authentication (el cliente lo obtiene del SDK de Firebase tras iniciar
sesión; el backend nunca ve ni guarda contraseñas). La primera vez que el backend ve un `uid`, crea el usuario
automáticamente con rol `estudiante` y `consentimiento_aceptado: false`.

**Errores comunes de autenticación/autorización** (aplican a cualquier endpoint protegido):

| Código | Cuándo | `detail` |
|---|---|---|
| 401 | Falta el header, no empieza con `Bearer `, o el token es inválido/expirado | `"Falta el encabezado Authorization: Bearer <id_token>."` o `"Token de Firebase inválido: ..."` |
| 403 | El usuario no tiene el rol requerido, o pide el perfil/historial de otro estudiante | `"Se requiere el rol docente o admin."` / `"No puedes acceder al perfil de otro estudiante."` |
| 409 | El estudiante no ha aceptado el consentimiento informado (solo en endpoints de chat) | `"Falta aceptar el consentimiento informado antes de usar el tutor. Acéptalo primero con POST /api/v1/usuarios/consentimiento."` |

Un estudiante (`rol: "estudiante"`) solo puede leer/modificar su propio perfil e historial; `docente`/`admin`
pueden consultar los de cualquiera. Subir o reindexar documentos exige rol `docente` o `admin`.

## Flujo de arranque recomendado para la app

1. Iniciar sesión con Firebase (fuera de este backend) y obtener el `id_token`.
2. `GET /api/v1/salud` (sin token) para saber si el backend está disponible antes de dejar escribir.
3. `GET /api/v1/usuarios/yo` para saber el rol y si falta el consentimiento.
4. Si `consentimiento_aceptado` es `false`: `POST /api/v1/usuarios/consentimiento`.
5. Usar `POST /api/v1/chat` normalmente; guardar el `conversacion_id` que devuelve para reutilizarlo en el
   mismo hilo de conversación.

---

## `GET /api/v1/salud`

Público, sin autenticación. Para que la app muestre si el backend está disponible antes de dejar escribir.

**Respuesta 200:**
```json
{
  "estado": "ok",
  "modelo": "llama3.2",
  "ollama_disponible": true,
  "documentos_indexados": 12,
  "chunks_indexados": 340
}
```
- `estado`: `"ok"` si Ollama responde, `"degradado"` si el servidor está arriba pero Ollama no contesta (la app
  puede seguir mostrando contenido cacheado/offline, pero `/chat` probablemente fallará o tardará en dar error).
- `modelo`: el modelo configurado (`MODELO_LLM`), cargado o no — Ollama no confirma aquí que el modelo esté
  descargado, solo que el servicio responde.
- `ollama_disponible`: resultado de una comprobación corta (2 s de margen) contra Ollama.
- `documentos_indexados` / `chunks_indexados`: tamaño actual del índice RAG.

No tiene códigos de error propios: si el proceso está vivo, responde 200 (con `estado: "degradado"` si hace
falta); si el proceso no está vivo, la petición ni siquiera llega (error de conexión del lado del cliente).

---

## `POST /api/v1/chat`

Requiere autenticación y consentimiento aceptado (409 si falta).

**Entrada:**
```json
{
  "mensaje": "¿Qué es la ISO 9001?",
  "conversacion_id": "a1b2c3d4e5f6...",
  "leccion_id": "leccion-iso-9001"
}
```
| Campo | Tipo | Obligatorio | Significado |
|---|---|---|---|
| `mensaje` | string | sí | La pregunta del estudiante. |
| `conversacion_id` | string (≤100) | no | Identifica la conversación: con el mismo id el tutor recuerda los turnos anteriores (memoria en RAM, se pierde si el servidor se reinicia). Si se omite, el servidor genera uno y lo devuelve; el cliente debe guardarlo y reenviarlo en los siguientes mensajes del mismo hilo. |
| `leccion_id` | string (≤100) | no | Id de una lección de la app (ver `configuracion/lecciones.json`). Si se reconoce, el tutor prioriza el tema del sílabo de esa lección al recuperar contexto — útil para que una pregunta ambigua dentro de una lección ("¿y eso qué significa?") se responda en el marco correcto. Un `leccion_id` desconocido no es un error: el tutor sigue el filtro de pertinencia normal, como si no se hubiera enviado. |

**Respuesta 200:**
```json
{
  "respuesta": "La ISO 9001 es la norma internacional de sistemas de gestión de la calidad...",
  "tipo": "respuesta",
  "conversacion_id": "a1b2c3d4e5f6...",
  "desde_cache": false,
  "latencia_ms": 2345.6,
  "tema_detectado": "ISO 9001",
  "unidad_detectada": 2,
  "tema_id_detectado": "2.2",
  "metodo_deteccion": "palabras_clave",
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

| Campo | Tipo | Significado |
|---|---|---|
| `respuesta` | string | Lo que dice el tutor. Nunca es la solución completa de un ejercicio (ver "Reglas del producto"). |
| `tipo` | string | Uno de `saludo`, `funcionamiento`, `sin_documentos`, `respuesta`, `sin_contexto`, `redireccion`, `error`. Ver tabla abajo. |
| `conversacion_id` | string | El mismo que se envió, o uno nuevo generado por el servidor. Guardarlo para el siguiente mensaje del hilo. |
| `desde_cache` | bool | `true` si la respuesta salió del caché semántico (sin llamar al modelo): responde en ~20 ms en vez de varios segundos. |
| `latencia_ms` | number | Cuánto tardó el servidor en producir la respuesta, en milisegundos. |
| `tema_detectado` | string \| null | Nombre del tema del sílabo al que pertenece la pregunta. `null` si se redirigió, es un saludo o una pregunta sobre el propio tutor. |
| `unidad_detectada` | int \| null | Número de unidad (1 a 4) del tema detectado. |
| `tema_id_detectado` | string \| null | Id exacto del tema en `configuracion/silabo.yaml` (p. ej. `"2.2"`). Campo adicional, no forma parte del contrato mínimo pedido pero no cuesta nada al cliente que lo ignore; útil para analítica. |
| `metodo_deteccion` | string \| null | Cómo se decidió la ubicación: `palabras_clave`, `llm`, `embedding`, `leccion` o `seguimiento`. También adicional. |
| `adaptacion` | object \| null | Cómo se adaptó la respuesta al perfil del estudiante (ver tabla). `null` solo en rutas que no se adaptan (saludo, redirección). |
| `posicion_en_cola` | int \| null | Cuántas peticiones había delante de esta cuando llegó al servidor (0 = pasó directo). `null` si no hubo que esperar o si la respuesta salió del caché. |
| `espera_estimada_s` | number \| null | Estimación de espera hecha al llegar (posición × media móvil de generaciones reales), en segundos. `null` junto con `posicion_en_cola`. |
| `espera_real_s` | number \| null | Lo que realmente tardó en conseguir un cupo de generación. Campo adicional (lo usa `scripts/prueba_concurrencia.py`); la app puede ignorarlo y usar `espera_estimada_s`. |

**Valores de `tipo`:**

| `tipo` | Significado |
|---|---|
| `saludo` | El mensaje era un saludo exacto ("hola", "buenas", etc.). Única respuesta predefinida del sistema. |
| `funcionamiento` | El estudiante preguntó sobre el propio tutor ("¿qué puedes hacer?"). |
| `sin_documentos` | El índice no tiene ningún documento cargado todavía. |
| `respuesta` | Respuesta normal, generada desde el contexto recuperado. |
| `sin_contexto` | La pregunta nombra algo (una norma, un acrónimo) que no está en los documentos indexados; el tutor lo dice y señala la unidad del sílabo correspondiente, sin inventar. |
| `redireccion` | La pregunta está fuera del temario del curso; el tutor no la responde, la redirige. |
| `error` | Ocurrió una excepción al generar (poco común); el texto del error va en `respuesta`. La petición HTTP sigue siendo 200. |

**`adaptacion` (objeto):**

| Campo | Tipo | Significado |
|---|---|---|
| `nivel` | string | `bajo`, `medio` o `alto`: franja estimada del estudiante en la unidad de esta consulta. |
| `profundidad` | string | `breve`, `media` o `extensa`: cuánto se extendió la explicación. |
| `estilo` | string | `conceptual`, `ejemplos` o `comparativo`. |
| `dificultad` | bool | El tema de esta consulta está entre los que le han costado al estudiante. |
| `segmento` | string | Identificador interno del ajuste aplicado (usado para el caché segmentado); `""` significa "sin ajuste" (estudiante nuevo o perfil neutro). |
| `referencias` | array | Temas ya trabajados por el estudiante en los que se apoyó la explicación (`tema_id`, `tema`, `unidad`); vacío si no aplica. |

**Errores:**

| Código | Causa | Cuerpo |
|---|---|---|
| 401 / 403 / 409 | Ver tabla de autenticación arriba. | ver arriba |
| 422 | `mensaje` ausente, o `conversacion_id`/`leccion_id` con más de 100 caracteres. | Error estándar de validación de FastAPI (`detail`: lista de errores por campo). |
| 503 | El tutor lleva más de `ESPERA_MAXIMA_COLA_S` (90 s por defecto) esperando un cupo de generación. | `"detail": "El tutor está saturado: más de 90 s esperando turno (posición al llegar: N). Intenta de nuevo en un momento."` |

### `GET /api/v1/cola/estado`

Público, sin autenticación (igual que `GET /salud`). Foto en vivo de la cola de generación, para mostrarla
mientras se espera la respuesta de un `/chat` anterior (la propia respuesta de `/chat` ya trae `posicion_en_cola`
y `espera_estimada_s` de ESA petición; este endpoint es para sondear el estado general sin mandar ninguna
pregunta).

**Respuesta 200:**
```json
{"limite": 2, "generando": 1, "en_espera": 0, "tiempo_medio_generacion_s": 6.42, "espera_maxima_s": 90.0}
```

---

## `GET /api/v1/usuarios/yo`

El usuario autenticado, para que la app sepa su rol y si ya aceptó el consentimiento sin decodificar el token.

**Respuesta 200:**
```json
{
  "uid": "abc123firebase",
  "correo": "estudiante@upec.edu.ec",
  "nombre": "Ana Pérez",
  "foto_url": null,
  "proveedor": "password",
  "rol": "estudiante",
  "fecha_registro": "2026-01-10T08:00:00+00:00",
  "ultimo_acceso": "2026-01-15T09:30:00+00:00",
  "consentimiento_aceptado": false,
  "consentimiento_fecha": null
}
```
`proveedor` es `password` o `google`. `rol` es `estudiante`, `docente` o `admin` (el rol se asigna manualmente en
la base de datos; no hay un endpoint para auto-asignarse `docente`/`admin`).

## `POST /api/v1/usuarios/consentimiento`

Registra que el estudiante aceptó el consentimiento informado. Sin esto, `/chat` responde 409. Sin cuerpo de
petición. Respuesta: igual forma que `GET /usuarios/yo`, con `consentimiento_aceptado: true` y
`consentimiento_fecha` con la fecha actual.

---

## `GET /api/v1/perfil/{uid}`

`uid` = el uid de Firebase del estudiante (403 si no es el propio y quien pregunta no es docente/admin).

**Respuesta 200:**
```json
{
  "user_id": "abc123firebase",
  "nivel_por_unidad": {"1": 3.0, "2": 2.8, "3": 3.0, "4": 3.0},
  "temas_consultados": {"2.2": 4, "2.5": 1},
  "temas_con_dificultad": ["2.2"],
  "profundidad_preferida": "media",
  "estilo_preferido": "conceptual",
  "ritmo": {"sesiones": 3, "mensajes_totales": 12, "mensajes_por_sesion": 4.0, "duracion_media_s": 180.5},
  "historial_resumido": [{"tema_id": "2.2", "tema": "ISO 9001", "unidad": 2, "fecha": "2026-01-15T09:00:00+00:00"}],
  "aclaraciones_por_tema": {"2.2": 2},
  "senales_recientes": ["confusion", "confusion"],
  "creado_en": "2026-01-10T08:05:00+00:00",
  "actualizado_en": "2026-01-15T09:30:00+00:00",
  "es_nuevo": false,
  "resumen_historial": "«ISO 9001» (Unidad 2)",
  "dificultades": [{"tema_id": "2.2", "tema": "ISO 9001", "unidad": 2}]
}
```
Un estudiante sin perfil guardado todavía recibe el perfil inicial (nivel 3.0 en las cuatro unidades) con
`es_nuevo: true`; no se crea nada hasta su primer mensaje en `/chat`.

## `GET /api/v1/perfil/{uid}/progreso`

Evolución del nivel estimado por unidad.

**Respuesta 200:**
```json
{
  "user_id": "abc123firebase",
  "unidades": [
    {"unidad": 1, "titulo": "Aplicación de metodología de desarrollo de software", "nivel_actual": 3.0,
     "puntos": [{"fecha": null, "nivel": 3.0, "motivo": "inicial", "tema_id": null}]},
    {"unidad": 2, "titulo": "Normativas de desarrollo y calidad del software", "nivel_actual": 2.8,
     "puntos": [{"fecha": null, "nivel": 3.0, "motivo": "inicial", "tema_id": null},
                {"fecha": "2026-01-15T09:10:00+00:00", "nivel": 2.6, "motivo": "confusion", "tema_id": "2.2"}]}
  ]
}
```
`motivo` es `inicial`, `confusion` o `reflexion_correcta`.

## `POST /api/v1/perfil/{uid}/reiniciar`

Borra el perfil del estudiante (vuelve al inicial); conserva su historial de conversaciones. Sin cuerpo.
Respuesta: igual forma que `GET /perfil/{uid}`, con `es_nuevo: true`.

---

## `GET /api/v1/progreso/mio`

Progreso de gamificación de la app (XP, racha, lecciones, ejercicios) del estudiante autenticado — siempre el
propio, no toma ningún uid del cliente.

**Respuesta 200:**
```json
{
  "xp_total": 150,
  "racha_actual": 3,
  "racha_mejor": 5,
  "ultima_actividad_fecha": "2026-01-15",
  "lecciones_completadas": 4,
  "ejercicios_resueltos": 10,
  "ejercicios_correctos": 7
}
```
Un estudiante sin actividad todavía recibe este mismo objeto en ceros (`ultima_actividad_fecha: null`), sin
crear ninguna fila hasta su primer evento.

## `POST /api/v1/progreso/lecciones/{leccion_id}/completar`

Registra una lección completada: suma XP y actualiza la racha (ver reglas abajo). Sin cuerpo de petición.
`leccion_id` es de uso libre por la app (no necesita existir en `configuracion/lecciones.json`: ese archivo solo
afecta a `/chat`). Respuesta: el progreso actualizado, misma forma que `GET /progreso/mio`.

## `POST /api/v1/progreso/ejercicios/{ejercicio_id}/resolver`

**Entrada:**
```json
{"correcto": true, "leccion_id": "leccion-iso-9001"}
```
| Campo | Tipo | Obligatorio | Significado |
|---|---|---|---|
| `correcto` | bool | sí | Si el estudiante resolvió el ejercicio correctamente. |
| `leccion_id` | string (≤100) | no | Solo informativo (queda registrado en el evento); no afecta el cálculo de XP. |

Respuesta: el progreso actualizado, misma forma que `GET /progreso/mio`.

**Reglas de XP y racha** (`app/services/progreso_service.py`):
- Lección completada: +20 XP. Ejercicio correcto: +10 XP. Ejercicio incorrecto: +2 XP (participación).
- La racha cuenta días consecutivos con al menos un evento: el primer evento del día la sube en 1 (o la pone en
  1 si hubo un hueco de más de un día); varios eventos el mismo día no la suben más de una vez. `racha_mejor` es
  el máximo histórico.

---

## `GET /api/v1/historial/conversaciones`

Las conversaciones del estudiante autenticado (persistidas en base de datos, a diferencia de la memoria en RAM
de `/chat`), más reciente primero.

**Respuesta 200:**
```json
[{"id": "a1b2c3...", "titulo": "¿Qué es la ISO 9001?", "fecha_inicio": "2026-01-15T09:00:00+00:00",
  "fecha_ultimo_mensaje": "2026-01-15T09:05:00+00:00"}]
```

## `GET /api/v1/historial/conversaciones/{conversation_id}/mensajes`

**Respuesta 200:**
```json
[{"rol": "estudiante", "contenido": "¿Qué es la ISO 9001?", "tipo": null, "fecha": "2026-01-15T09:00:00+00:00"},
 {"rol": "tutor", "contenido": "La ISO 9001 es...", "tipo": "respuesta", "fecha": "2026-01-15T09:00:02+00:00"}]
```
404 si la conversación no existe o no es del estudiante autenticado (no se distingue uno de otro, para no poder
confirmar la existencia de conversaciones ajenas tanteando ids).

---

## `GET /api/v1/docente/estadisticas` (solo `docente`/`admin`)

Query opcional: `dias_actividad_reciente` (1 a 90, por defecto 7).

**Respuesta 200 (resumida):**
```json
{
  "estudiantes_totales": 42,
  "estudiantes_activos": 30,
  "dias_actividad_reciente": 7,
  "preguntas_por_unidad": [{"unidad": 1, "titulo": "...", "preguntas": 120}],
  "temas_con_mas_dificultad": [{"tema_id": "2.2", "tema": "ISO 9001", "unidad": 2, "estudiantes": 8}],
  "evolucion_por_unidad": [{"unidad": 1, "titulo": "...", "nivel_medio_actual": 3.1, "cambio_medio": 0.1}],
  "progreso_app": {
    "estudiantes_con_progreso": 25,
    "xp_total_acumulado": 3400,
    "lecciones_completadas_total": 95,
    "ejercicios_resueltos_total": 210,
    "ejercicios_correctos_total": 160,
    "racha_actual_media": 2.4
  }
}
```
`progreso_app` agrega `progreso_estudiante` (lo que registran los endpoints de `/progreso`): nunca expone el
detalle de un estudiante en particular, solo sumas/promedios (para eso está `/perfil/{uid}`, con control de
propietario). 403 si quien pregunta no es docente/admin.

---

## `GET /api/v1/cache/estadisticas`

Sin restricción de rol (cualquier estudiante autenticado puede verlas; son agregadas, no por estudiante). 503 si
`CACHE_ACTIVO=false`.

**Respuesta 200 (forma):**
```json
{
  "total_entradas": 80, "consultas": 500, "aciertos": 210, "fallos": 290, "tasa_aciertos": 0.42,
  "preguntas_mas_repetidas": [{"pregunta": "¿Qué es la ISO 9001?", "usos": 12}],
  "tiempo_promedio_ahorrado_ms": 6200.0, "tiempo_total_ahorrado_ms": 1302000.0,
  "umbral_similitud": 0.95, "invalidaciones": 3, "ultima_invalidacion": "2026-01-10T12:00:00+00:00",
  "motivo_ultima_invalidacion": "reindexado", "entradas_por_segmento": {"": 40, "n=bajo|p=extensa": 10},
  "omitidos_por_perfil": 15
}
```

---

## Documentos (solo `docente`/`admin` para subir/reindexar; listar es público)

### `GET /api/v1/documentos`

Lista los `.md` de `documentacion/markdown/` con su estado en el índice (no requiere rol especial, pero sí
autenticación como cualquier otro endpoint salvo `/salud`).

```json
{"total_chunks": 340, "documentos": [{"nombre": "iso_9001.md", "indexado": true, "chunks": 28,
  "fecha_indexado": "2026-01-05T10:00:00+00:00",
  "archivos": {"original": "iso_9001.pdf", "pdf": "iso_9001.pdf", "markdown": "iso_9001.md"}}]}
```

### `POST /api/v1/documentos/subir` (`docente`/`admin`)

`multipart/form-data`, campo `archivos` (alias `files`): uno o varios PDF/DOCX/PPTX/TXT/MD.

```json
{
  "resultados": [{"nombre": "iso_9001.pdf", "rutas": {"original": "documentacion/originales/iso_9001.pdf",
    "pdf": "documentacion/pdf/iso_9001.pdf", "markdown": "documentacion/markdown/iso_9001.md"},
    "chunks_indexados": 28, "estado": "indexado", "detalle": null}],
  "resumen": {"total": 1, "indexados": 1, "omitidos_sin_cambios": 0, "errores": 0}
}
```
`estado` es `indexado`, `omitido_sin_cambios` (el archivo no cambió) o `error` (ver `detalle`). Un archivo
rechazado nunca aborta el resto del lote. 422 si no se envía ningún archivo.

### `POST /api/v1/documentos/reindexar` (`docente`/`admin`)

Mantenimiento: reconstruye todo el índice desde `documentacion/markdown/`. Sin cuerpo; devuelve
`{"documentos": N, "chunks": M, "resultados": [...]}`.

---

## CORS

`allow_origins=["*"]`, `allow_credentials=False`, todos los métodos y headers permitidos — sirve tanto a la
página de prueba (`GET /`) como al cliente Flutter (web, Android, iOS), sin la combinación inválida
`allow_origins=["*"]` + `allow_credentials=True` (los navegadores la rechazan). No hace falta `credentials`
porque la identidad viaja en el header `Authorization`, no en cookies.

## Notas para quien integre la app

- El campo `leccion_id` de `/chat` y las claves de `configuracion/lecciones.json` deben coincidir exactamente
  (sensible a mayúsculas/minúsculas); una lección no mapeada no es un error, simplemente no prioriza nada.
- `conversacion_id` es por hilo de chat, no por sesión de la app: cerrar y reabrir la app sin cambiar de pantalla
  de chat debería seguir enviando el mismo id si se quiere que el tutor recuerde el contexto (la memoria vive en
  RAM del servidor y se pierde si este se reinicia; el historial persistente de `/historial` es para mostrar
  conversaciones pasadas, no para que el tutor "recuerde" automáticamente al reabrirlas).
- El tutor **nunca** entrega la solución completa de un ejercicio: en `tipo: respuesta` dentro de una "tarea"
  (petición de resolver algo), la respuesta trae pasos numerados y pistas, nunca el trabajo terminado.
