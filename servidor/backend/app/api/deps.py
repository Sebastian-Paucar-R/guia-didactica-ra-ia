"""Dependencias de FastAPI para identidad (Firebase), consentimiento informado y roles.

Ninguna guarda una contraseña: `usuario_actual` verifica el `id_token` de Firebase del encabezado
`Authorization: Bearer <id_token>` (app.core.firebase_auth) y, la primera vez que ve ese `uid`, crea la fila en
`usuarios` con lo que Firebase ya verificó (correo, nombre, foto, proveedor). El resto de la app (perfil, chat,
historial) siempre recibe el usuario ya autenticado, nunca un `user_id` que el cliente pueda inventar.
"""
from datetime import datetime, timezone

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.core import firebase_auth
from app.db.models import Usuario
from app.db.session import get_db


def _ahora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _proveedor_de(claims: dict) -> str:
    crudo = (claims.get("firebase") or {}).get("sign_in_provider", "") or ""
    return "google" if "google" in crudo else "password"


def _extraer_token(authorization: str | None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Falta el encabezado Authorization: Bearer <id_token>.")
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=401, detail="Falta el encabezado Authorization: Bearer <id_token>.")
    return token


def usuario_actual(authorization: str | None = Header(default=None), db: Session = Depends(get_db)) -> Usuario:
    """Verifica el token y devuelve el usuario, creándolo (rol `estudiante`, sin consentimiento aceptado) la
    primera vez que se ve su `uid`. Actualiza `ultimo_acceso` en cada llamada; 401 si el token falta o no es
    válido (expirado, revocado, mal firmado: lo que sea que lance firebase_admin.auth.verify_id_token)."""
    token = _extraer_token(authorization)
    try:
        claims = firebase_auth.verificar_token(token)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Token de Firebase inválido: {type(e).__name__}: {e}")

    uid = claims.get("uid") or claims.get("sub")
    if not uid:
        raise HTTPException(status_code=401, detail="El token no trae un uid.")

    ahora = _ahora()
    usuario = db.get(Usuario, uid)
    if usuario is None:
        usuario = Usuario(
            uid_firebase=uid, correo=claims.get("email", ""), nombre=claims.get("name"),
            foto_url=claims.get("picture"), proveedor=_proveedor_de(claims), rol="estudiante",
            fecha_registro=ahora, ultimo_acceso=ahora, consentimiento_aceptado=False)
        db.add(usuario)
    else:
        usuario.ultimo_acceso = ahora
        # Lo que puede cambiar en Firebase (nombre, foto, correo) se refresca; rol y consentimiento son de esta
        # app y Firebase no los conoce.
        if claims.get("email"):
            usuario.correo = claims["email"]
        if claims.get("name"):
            usuario.nombre = claims["name"]
        if claims.get("picture"):
            usuario.foto_url = claims["picture"]
    db.commit()
    db.refresh(usuario)
    return usuario


def usuario_con_consentimiento(usuario: Usuario = Depends(usuario_actual)) -> Usuario:
    """Igual que `usuario_actual`, pero exige el consentimiento informado ya aceptado: 409 si no (regla del
    encargo: los endpoints de chat no funcionan sin él)."""
    if not usuario.consentimiento_aceptado:
        raise HTTPException(status_code=409, detail=(
            "Falta aceptar el consentimiento informado antes de usar el tutor. Acéptalo primero con "
            "POST /api/v1/usuarios/consentimiento."))
    return usuario


def requiere_rol(*roles: str):
    """Dependencia parametrizada: 403 si el usuario autenticado no tiene uno de estos roles.
    Uso: `Depends(requiere_rol("docente", "admin"))`."""
    def _verificar(usuario: Usuario = Depends(usuario_actual)) -> Usuario:
        if usuario.rol not in roles:
            raise HTTPException(status_code=403, detail=f"Se requiere el rol {' o '.join(roles)}.")
        return usuario
    return _verificar


def verificar_propietario(usuario: Usuario, uid_objetivo: str) -> None:
    """403 si `usuario` pide el perfil/historial de otro estudiante y no es docente ni admin. Un estudiante solo
    puede leer o modificar su propio perfil (regla del encargo); docente/admin pueden consultar cualquiera."""
    if usuario.uid_firebase != uid_objetivo and usuario.rol not in ("docente", "admin"):
        raise HTTPException(status_code=403, detail="No puedes acceder al perfil de otro estudiante.")
