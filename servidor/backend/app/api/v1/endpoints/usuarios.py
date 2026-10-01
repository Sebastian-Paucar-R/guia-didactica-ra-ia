from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import usuario_actual
from app.db.models import Usuario
from app.db.session import get_db

router = APIRouter(prefix="/usuarios", tags=["usuarios"])


class UsuarioRespuesta(BaseModel):
    uid: str
    correo: str
    nombre: str | None
    foto_url: str | None
    proveedor: str
    rol: str
    fecha_registro: str
    ultimo_acceso: str
    consentimiento_aceptado: bool
    consentimiento_fecha: str | None


def _respuesta(u: Usuario) -> UsuarioRespuesta:
    return UsuarioRespuesta(
        uid=u.uid_firebase, correo=u.correo, nombre=u.nombre, foto_url=u.foto_url, proveedor=u.proveedor,
        rol=u.rol, fecha_registro=u.fecha_registro, ultimo_acceso=u.ultimo_acceso,
        consentimiento_aceptado=u.consentimiento_aceptado, consentimiento_fecha=u.consentimiento_fecha)


@router.get("/yo", response_model=UsuarioRespuesta)
def yo(usuario: Usuario = Depends(usuario_actual)):
    """El usuario autenticado (para que la app sepa su rol y si ya aceptó el consentimiento sin tener que
    decodificar el token ella misma)."""
    return _respuesta(usuario)


@router.post("/consentimiento", response_model=UsuarioRespuesta)
def aceptar_consentimiento(usuario: Usuario = Depends(usuario_actual), db: Session = Depends(get_db)):
    """Registra que el estudiante aceptó el consentimiento informado, con fecha. Sin esto, los endpoints de
    chat responden 409 (ver app/api/deps.py:usuario_con_consentimiento)."""
    usuario.consentimiento_aceptado = True
    usuario.consentimiento_fecha = datetime.now(timezone.utc).isoformat(timespec="seconds")
    db.commit()
    db.refresh(usuario)
    return _respuesta(usuario)
