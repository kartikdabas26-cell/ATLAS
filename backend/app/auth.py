from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from threading import Lock

from dotenv import load_dotenv
from fastapi import HTTPException, Request


load_dotenv(Path(__file__).resolve().parents[1] / ".env")


@dataclass(frozen=True)
class AuthUser:
    subject: str
    email: str
    name: str
    picture: str | None = None


class AuthenticationError(Exception):
    """Raised when a Firebase ID token cannot be verified."""


_firebase_app = None
_firebase_lock = Lock()



def _firebase_admin_app():
    global _firebase_app
    if _firebase_app is not None:
        return _firebase_app
    try:
        import firebase_admin
        from firebase_admin import credentials

        with _firebase_lock:
            if _firebase_app is None:
                credential_json = os.environ.get(
                    "FIREBASE_ADMIN_CREDENTIALS_JSON",
                    "",
                ).strip()
                if credential_json:
                    credential = credentials.Certificate(json.loads(credential_json))
                else:
                    credential = credentials.ApplicationDefault()
                _firebase_app = firebase_admin.initialize_app(credential)
        return _firebase_app
    except Exception as exc:
        raise AuthenticationError("Firebase authentication is unavailable.") from exc


def verify_firebase_id_token(token: str) -> AuthUser:
    if not token:
        raise AuthenticationError("Missing Firebase ID token.")

    try:
        import firebase_admin.auth

        decoded = firebase_admin.auth.verify_id_token(
            token,
            app=_firebase_admin_app(),
        )
        if not isinstance(decoded, dict):
            raise AuthenticationError("Invalid Firebase ID token.")
    except Exception as exc:
        raise AuthenticationError("Invalid Firebase ID token.") from exc

    subject = str(decoded.get("uid") or decoded.get("sub") or "").strip()
    if not subject:
        raise AuthenticationError("Invalid Firebase user identity.")
    return AuthUser(
        subject=subject,
        email=str(decoded.get("email") or "").strip().lower(),
        name=str(decoded.get("name") or decoded.get("email") or subject),
        picture=decoded.get("picture"),
    )


def get_current_user(request: Request) -> AuthUser:
    user = getattr(request.state, "atlas_user", None)
    if user is not None:
        return user
    authorization = request.headers.get("Authorization", "")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(status_code=401, detail="Authentication required.")
    try:
        return verify_firebase_id_token(token.strip())
    except AuthenticationError as exc:
        raise HTTPException(status_code=401, detail="Authentication required.") from exc


def authenticate_request(request: Request) -> AuthUser:
    return get_current_user(request)
