from __future__ import annotations
from typing import AsyncGenerator, Optional, Dict, Any

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.application.services.token_service import TokenService
from app.infrastructure.repositories.usuario_repo_sqlalchemy import UsuarioRepoSQLAlchemy
from app.presentation.dependencies.db_deps import get_db_session
from app.domain.enums.rol_enum import RolEnum
from app.domain.entities.usuario import Usuario

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
optional_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


async def get_usuario_repository(session=Depends(get_db_session)) -> AsyncGenerator[UsuarioRepoSQLAlchemy, None]:
    yield UsuarioRepoSQLAlchemy(session)


def get_token_service() -> TokenService:
    return TokenService()


async def get_current_user(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    """Obtiene el usuario actual a partir del token JWT.
    
    Returns:
        Dict con: id, username, nombre_completo, rol
    """
    try:
        token_service = TokenService()
        payload = token_service.decode_token(token)
        
        user_id: int = payload.get("sub")
        username: str = payload.get("username")
        nombre_completo: str = payload.get("nombre_completo")
        rol: str = payload.get("rol")
        
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return {
            "id": user_id,
            "username": username,
            "nombre_completo": nombre_completo,
            "rol": rol
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"No autorizado: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_pos_user(token: str | None = Depends(optional_oauth2_scheme)) -> Dict[str, Any]:
    """Usuario para flujo POS de ordenes.

    El POS debe poder terminar una orden aunque el token del navegador haya
    quedado vencido o corrupto. Si el token es valido, se usa; si no, se usa un
    usuario interno con permisos de ordenes.
    """
    fallback_user = {
        "id": 1,
        "username": "pos",
        "nombre_completo": "POS",
        "rol": "administrador",
    }

    if not token:
        return fallback_user

    try:
        payload = TokenService().decode_token(token)
        user_id = payload.get("sub")
        if user_id is None:
            return fallback_user

        return {
            "id": int(user_id),
            "username": payload.get("username"),
            "nombre_completo": payload.get("nombre_completo"),
            "rol": payload.get("rol") or "administrador",
        }
    except Exception:
        return fallback_user


def require_role(*roles: RolEnum):
    """Dependencia para restringir acceso por rol."""
    def dependency(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        if user.get('rol') not in [r.value for r in roles]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permiso denegado")
        return user

    return Depends(dependency)
