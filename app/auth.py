from __future__ import annotations

from typing import Annotated
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from app.config import get_settings

bearer_scheme = HTTPBearer(auto_error=False)


class TokenPayload(BaseModel):
    sub: str                        # user UUID (auth.uid())
    email: str | None = None
    role: str | None = None         # 'admin' si está en user_metadata
    user_metadata: dict = {}


def _decode_supabase_jwt(token: str) -> TokenPayload:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            options={"verify_aud": False},
        )
        metadata = payload.get("user_metadata", {})
        return TokenPayload(
            sub=payload["sub"],
            email=payload.get("email"),
            role=metadata.get("role"),
            user_metadata=metadata,
        )
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


# ── Dependencias ──────────────────────────────────────────────

def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Security(bearer_scheme)
    ] = None,
) -> TokenPayload:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No se proporcionó token de autenticación",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return _decode_supabase_jwt(credentials.credentials)


def get_current_admin(
    user: Annotated[TokenPayload, Depends(get_current_user)],
) -> TokenPayload:
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requieren permisos de administrador",
        )
    return user


def get_current_docente(
    user: Annotated[TokenPayload, Depends(get_current_user)],
) -> TokenPayload:
    """Acepta tanto docentes como admins."""
    if user.role not in ("docente", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requieren permisos de docente",
        )
    return user


# Alias tipados para usar con Annotated en los routers
CurrentUser    = Annotated[TokenPayload, Depends(get_current_user)]
CurrentAdmin   = Annotated[TokenPayload, Depends(get_current_admin)]
CurrentDocente = Annotated[TokenPayload, Depends(get_current_docente)]
