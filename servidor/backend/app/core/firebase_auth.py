"""Verificación de identidad con Firebase Authentication. Este proyecto nunca guarda una contraseña: Firebase
verifica quién es el estudiante (Google o correo/clave) y aquí solo se confía en el token que ya validó.

`verificar_token` es una función de módulo (no un método de clase) a propósito: en las pruebas se sustituye
directamente (`monkeypatch.setattr(firebase_auth, "verificar_token", falso)`), igual que el resto del proyecto
sustituye el LLM o los embeddings, sin necesitar credenciales reales de Firebase ni red.
"""
import firebase_admin
from firebase_admin import auth as _auth_sdk
from firebase_admin import credentials

from app.core.config import settings

_app: firebase_admin.App | None = None


def _app_firebase() -> firebase_admin.App:
    global _app
    if _app is None:
        if not settings.FIREBASE_CREDENTIALS_PATH:
            raise RuntimeError(
                "FIREBASE_CREDENTIALS_PATH no está configurado (ver .env.example): sin la credencial de la "
                "cuenta de servicio no se puede verificar ningún token de Firebase.")
        cred = credentials.Certificate(str(settings.FIREBASE_CREDENTIALS_PATH))
        _app = firebase_admin.initialize_app(cred)
    return _app


def verificar_token(id_token: str) -> dict:
    """Claims del token ya verificado (uid, email, name, picture, firebase.sign_in_provider, ...). Lanza la
    excepción de firebase_admin.auth que corresponda (ExpiredIdTokenError, InvalidIdTokenError, ...) si no es
    válido; quien llama (app/api/deps.py) la traduce a un 401."""
    return _auth_sdk.verify_id_token(id_token, app=_app_firebase())
