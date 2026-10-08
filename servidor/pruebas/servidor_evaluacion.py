"""Servidor para las evaluaciones por HTTP (pruebas/evaluar_tutor.py, scripts/evaluar_pertinencia.py), aislado.

Desde que POST /api/v1/chat exige un token de Firebase, esos scripts (que no envían ninguno) ya no podían correr
contra un servidor normal. Este lanzador hace lo mismo que backend/scripts/prueba_concurrencia.py: sustituye la
dependencia `usuario_actual` por un estudiante de evaluación ya consentido, dentro del proceso; ningún servidor
arrancado de la forma habitual (iniciar_servidor.bat) acepta peticiones sin token.

Todo lo que el servidor escribiría va a una carpeta temporal nueva, así que la evaluación nunca toca ni repite
datos reales: índice vectorial (se reindexa desde documentacion/markdown con el modelo de settings), caché
semántico vacío (un caché viejo devolvería respuestas de antes del cambio que se quiere medir) y base relacional.
PERFIL_ACTIVO=false: las preguntas se responden sin perfil adaptativo, como en las rondas oficiales anteriores (un
perfil que evoluciona a lo largo de 60 preguntas cambiaría el segmento del caché y el texto de las respuestas).

Uso (desde servidor/):
    python pruebas/servidor_evaluacion.py [--puerto 8020]
    python pruebas/evaluar_tutor.py --url http://127.0.0.1:8020 --robustez --etiqueta "..."
Cualquier variable de entorno ya definida (p. ej. RECUPERACION_HIBRIDA=false) tiene prioridad.
"""
import argparse
import os
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
TMP = Path(tempfile.mkdtemp(prefix="servidor_evaluacion_"))
os.environ.setdefault("BASE_VECTORIAL_DIR", str(TMP / "base_vectorial"))
os.environ.setdefault("CACHE_DB_PATH", str(TMP / "cache_respuestas.db"))
os.environ.setdefault("DATABASE_URL", f"sqlite:///{(TMP / 'tutor.db').as_posix()}")
os.environ.setdefault("PERFIL_ACTIVO", "false")
os.environ.setdefault("PYTHONUTF8", "1")
sys.path.insert(0, str(RAIZ / "backend"))

import uvicorn  # noqa: E402

from app.api.deps import usuario_actual  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.db import models  # noqa: E402,F401  (registra las tablas)
from app.db.base import Base  # noqa: E402
from app.db.models import Usuario  # noqa: E402
from app.db.session import crear_engine, crear_sessionmaker  # noqa: E402
from app.main import app  # noqa: E402

UID = "evaluacion"
AHORA = "2026-01-01T00:00:00+00:00"


def _estudiante() -> Usuario:
    return Usuario(uid_firebase=UID, correo="evaluacion@prueba.local", nombre="Evaluación", foto_url=None,
                   proveedor="password", rol="estudiante", fecha_registro=AHORA, ultimo_acceso=AHORA,
                   consentimiento_aceptado=True, consentimiento_fecha=AHORA)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--puerto", type=int, default=8020)
    args = ap.parse_args()

    # Esquema y estudiante en la base temporal: conversaciones/mensajes tienen clave foránea a usuarios
    Base.metadata.create_all(crear_engine(settings.DATABASE_URL))
    with crear_sessionmaker(database_url=settings.DATABASE_URL)() as ses:
        ses.add(_estudiante())
        ses.commit()
    app.dependency_overrides[usuario_actual] = _estudiante

    print(f"[EVAL] Carpeta temporal: {TMP}")
    print(f"[EVAL] Embeddings={settings.MODELO_EMBEDDINGS}  RECUPERACION_HIBRIDA={settings.RECUPERACION_HIBRIDA}  "
          f"PERFIL_ACTIVO={settings.PERFIL_ACTIVO}  MODELO_LLM={settings.MODELO_LLM}")
    uvicorn.run(app, host="127.0.0.1", port=args.puerto, log_level="warning")


if __name__ == "__main__":
    main()
