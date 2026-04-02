from __future__ import annotations

from typing import Annotated
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel
import httpx

from app.config import get_settings

bearer_scheme = HTTPBearer(auto_error=False)

# Cache de claves públicas de Supabase
_jwks_cache: dict | None = None


class TokenPayload(BaseModel):
    sub: str
    email: str | None = None
    role: str | None = None
    user_metadata: dict = {}


def _get_supabase_jwks() -> dict:
    global _jwks_cache
    if _jwks_cache is None:
        settings = get_settings()
        url = f"{settings.supabase_url}/auth/v1/.well-known/jwks.json"
        response = httpx.get(url, timeout=10)
        response.raise_for_status()
        _jwks_cache = response.json()
    return _jwks_cache


def _decode_supabase_jwt(token: str) -> TokenPayload:
    settings = get_settings()
    try:
        unverified_header = jwt.get_unverified_header(token)
        alg = unverified_header.get("alg", "HS256")

        if alg == "HS256":
            payload = jwt.decode(
                token,
                settings.supabase_jwt_secret,
                algorithms=["HS256"],
                options={"verify_aud": False},
            )
        else:
            # ES256 — validar con clave pública JWKS
            jwks = _get_supabase_jwks()
            kid = unverified_header.get("kid")
            public_key = None
            for key in jwks.get("keys", []):
                if key.get("kid") == kid:
                    public_key = key
                    break
            if not public_key:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Clave pública no encontrada para validar el token",
                )
            payload = jwt.decode(
                token,
                public_key,
                algorithms=["ES256"],
                options={"verify_aud": False},
            )

        metadata = payload.get("user_metadata", {})
        return TokenPayload(
            sub=payload["sub"],
            email=payload.get("email"),
            role=metadata.get("role"),
            user_metadata=metadata,
        )
    except HTTPException:
        raise
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
    if user.role not in ("docente", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requieren permisos de docente",
        )
    return user


# Alias tipados
CurrentUser    = Annotated[TokenPayload, Depends(get_current_user)]
CurrentAdmin   = Annotated[TokenPayload, Depends(get_current_admin)]
CurrentDocente = Annotated[TokenPayload, Depends(get_current_docente)]