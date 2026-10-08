# guia-didactica-ra-ia

Guía Didáctica Interactiva de Realidad Aumentada con IA para Normativas de Ingeniería de Software.

`servidor/` es el backend (FastAPI): un tutor con RAG sobre normas ISO/IEC/IEEE, perfilado adaptativo del
estudiante, identidad con Firebase Authentication y persistencia relacional. `normativas_app/` es el cliente
Flutter. Este README documenta cómo levantar el backend; ver `CLAUDE.md` para la arquitectura completa.

## Requisitos

- Python 3.14 (ver `servidor/backend/requirements.txt`).
- [Ollama](https://ollama.com) corriendo localmente, con el modelo de `MODELO_LLM` descargado
  (`ollama pull llama3.2`).
- Un proyecto de [Firebase](https://console.firebase.google.com/) con Authentication activado (Google y/o
  correo/contraseña) — para identidad del estudiante/docente. Sin él configurado, el servidor arranca igual,
  pero ningún endpoint protegido funciona (falla con un mensaje claro, no uno críptico).
- PostgreSQL, solo para un despliegue real con varios estudiantes concurrentes. Para desarrollo local no hace
  falta instalar nada: por defecto se usa SQLite en un archivo.

## Configuración

```
cd servidor/backend
pip install -r requirements.txt
copy .env.example .env      # (o `cp` en Linux/Mac) y completa los valores
```

Variables relevantes (`.env`, ver `.env.example` y `app/core/config.py` para la lista completa y sus valores
por defecto):

| Variable | Para qué | Por defecto |
|---|---|---|
| `DATABASE_URL` | Base relacional (usuarios, perfiles, conversaciones/mensajes, eventos_perfil) | SQLite en `servidor/tutor.db` |
| `FIREBASE_CREDENTIALS_PATH` | JSON de la cuenta de servicio de Firebase (verificar tokens) | sin configurar |
| `MODELO_LLM` / `MODELO_CLASIFICADOR` | Modelo de Ollama para generar / para clasificar (ver `reportes/comparativa_modelos.md`) | `llama3.2` / el mismo que `MODELO_LLM` |
| `LIMITE_GENERACIONES_SIMULTANEAS` | Cupos de la cola de generación (`services/cola_service.py`) | `2` |
| `ESPERA_MAXIMA_COLA_S` | Tope de espera en cola antes de responder 503 | `120` |

### Firebase Authentication

1. En la [consola de Firebase](https://console.firebase.google.com/), crea un proyecto (o usa uno existente) y
   activa **Authentication** con los proveedores que quieras (Google, correo/contraseña).
2. **Configuración del proyecto → Cuentas de servicio → Generar nueva clave privada**: descarga el JSON.
   **Nunca lo subas al repositorio** (el `.gitignore` ya excluye `*firebase*service*account*.json` y
   `*firebase-adminsdk*.json`, pero igual consérvalo fuera de `servidor/`).
3. `FIREBASE_CREDENTIALS_PATH=` en `.env`, apuntando a ese archivo.
4. En el cliente (Flutter), configura el mismo proyecto de Firebase y añade `google-services.json` /
   `GoogleService-Info.plist` (tampoco se versionan). El cliente inicia sesión con Firebase, obtiene un
   `id_token` y lo manda en cada petición como `Authorization: Bearer <id_token>`.

Sin `FIREBASE_CREDENTIALS_PATH` configurado, `core/firebase_auth.py` lanza un error explícito la primera vez
que un endpoint protegido intenta verificar un token, en vez de fallar de forma críptica dentro de la SDK.

### Base de datos

Migraciones con Alembic (`servidor/backend/alembic/`); no se versiona el estado de la base, solo el esquema:

```
cd servidor/backend
python scripts/inicializar_db.py        # equivalente a `alembic upgrade head`
```

Para PostgreSQL, `DATABASE_URL=postgresql+pg8000://usuario:clave@host:5432/basededatos` (el driver es
[`pg8000`](https://github.com/tlocke/pg8000), puro Python — no `psycopg2`, para evitar depender de un binario
nativo que en algunos entornos Windows queda bloqueado por una directiva de Control de aplicaciones; ver
`app/db/session.py`). Corre `python scripts/inicializar_db.py` contra esa URL antes de arrancar el servidor.
Una migración nueva: `alembic revision -m "descripción"` y editar el archivo generado en `alembic/versions/`
(o `--autogenerate` si el modelo cambió y la base de comparación está accesible).

## Arrancar el servidor

```
cd servidor
servidor\iniciar_servidor.bat
```

o manualmente (Windows; ver el `.bat` para el equivalente exacto):

```
cd servidor
set PYTHONPATH=backend
python -m uvicorn app.main:app --reload --port 8000 --app-dir backend
```

`GET /` sirve una página de prueba con chat y lista de documentos; `POST /api/v1/chat` exige
`Authorization: Bearer <id_token>` y, la primera vez, aceptar el consentimiento informado
(`POST /api/v1/usuarios/consentimiento`) — si no, responde 409.

## Precalentar el caché antes de una sesión

```
cd servidor/backend
python ../pruebas/precalentar_cache.py
```

Corre las preguntas de `configuracion/preguntas_frecuentes.json` (editable: una lista por unidad del sílabo)
contra el RAG real, para que las más probables respondan desde caché en milisegundos en vez de esperar la
primera generación real. No necesita el servidor arrancado ni un token de Firebase (instancia el RAG en
proceso).

## Pruebas

```
cd servidor/backend
python -m pytest
```

Ninguna prueba toca la base de datos, el caché ni el índice vectorial reales (fixtures de
`tests/conftest.py`: cada prueba recibe su propia base SQLite temporal, ya migrada). Las pruebas que ejercitan
el LLM lo sustituyen por una versión de mentira (`LLMFalso`): no requieren Ollama corriendo. La verificación de
Firebase se sustituye de la misma forma (`app.core.firebase_auth.verificar_token`, ver `tests/test_auth.py`).

### Evaluaciones extendidas (contra el servidor real)

`pruebas/evaluar_tutor.py`, `pruebas/evaluar_adaptacion.py`, `pruebas/auditar_cobertura.py` y
`backend/scripts/prueba_concurrencia.py` corren contra un servidor real con Ollama. Para no tocar los datos
reales, apunta `BASE_VECTORIAL_DIR` a una copia y `CACHE_DB_PATH` / `DATABASE_URL` a archivos nuevos antes de
arrancar el servidor (ver el docstring de cada script para el detalle). `prueba_concurrencia.py` no necesita
servidor aparte ni credenciales de Firebase: llama a la app ASGI en el mismo proceso y sustituye la identidad
por un estudiante de prueba ya consentido; el resultado de la última corrida está en
`reportes/prueba_concurrencia.md`.

## Endpoints principales

Todos bajo `/api/v1`. Los de chat, perfil e historial exigen `Authorization: Bearer <id_token>` (Firebase); los
de documentos (subir/reindexar) exigen además rol `docente` o `admin`; los de estadísticas docentes exigen
`docente`/`admin`.

| Método y ruta | Qué hace |
|---|---|
| `POST /chat` | Pregunta al tutor. Exige consentimiento informado aceptado (409 si no). |
| `GET /cola/estado` | Foto en vivo de la cola de generación. |
| `GET /usuarios/yo` | El usuario autenticado (rol, consentimiento). |
| `POST /usuarios/consentimiento` | Acepta el consentimiento informado. |
| `GET /perfil/{uid}` · `/progreso` · `POST /perfil/{uid}/reiniciar` | Perfil adaptativo. Un estudiante solo puede acceder al suyo. |
| `GET /historial/conversaciones` · `/{id}/mensajes` | Historial de conversaciones del estudiante autenticado. |
| `POST /documentos/subir` · `POST /documentos/reindexar` | Carga y reindexado de la base documental (docente/admin). |
| `GET /documentos` | Lista de documentos indexados (público). |
| `GET /docente/estadisticas` | Estudiantes activos, preguntas por unidad, temas con más dificultad, evolución del nivel (docente/admin). |
| `GET /cache/estadisticas` | Métricas del caché semántico. |
