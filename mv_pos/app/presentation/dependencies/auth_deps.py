from __future__ import annotations

from typing import Any, AsyncGenerator, Dict

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
    """
    CONCEPTO: La "aduana" de cada request autenticado.

    Cada endpoint que Depends(get_current_user) pasa por aquí.
    El JWT se decodifica, se verifican firma y expiración, y se retorna
    un dict con los datos del usuario — incluyendo restaurante_id.

    El restaurante_id en el dict se usa en require_role y en los routers
    para operaciones que necesiten saber a qué restaurante pertenece el user.

    IMPORTANTE: get_db_session ya leyó el restaurante_id del JWT para
    conectarse al DB correcto. Aquí lo leemos de nuevo para incluirlo
    en el contexto del usuario. Doble lectura, pero es barata (sin I/O).
    """
    try:
        token_service = TokenService()
        payload = token_service.decode_token(token)

        user_id: int = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return {
            "id": int(user_id),
            "username": payload.get("username"),
            "nombre_completo": payload.get("nombre_completo"),
            "rol": payload.get("rol"),
            "restaurante_id": payload.get("restaurante_id"),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"No autorizado: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_pos_user(token: str | None = Depends(optional_oauth2_scheme)) -> Dict[str, Any]:
    """
    CONCEPTO: Usuario para el flujo POS de órdenes.

    PROBLEMA ORIGINAL (antes):
        Si no había token, retornaba {id:1, rol:"administrador"} hardcodeado.
        En multi-tenant esto es un AGUJERO DE SEGURIDAD CRÍTICO:
        cualquier request sin token obtenía acceso de administrador
        al primer restaurante de la DB — inaceptable.

    SOLUCIÓN ACTUAL:
        - Sin token → 401 (ya no hay fallback anónimo).
        - Token válido → datos reales del usuario.
        - Token VENCIDO → aún extraemos los datos (decode sin verificar exp).
          Esto preserva el comportamiento POS original: si el mesero dejó
          la tablet sin usar y el token venció, puede seguir cerrando órdenes
          sin re-loguearse. La firma sí se verifica — no se puede falsificar.

    Por qué es aceptable decodificar un token vencido para POS:
        La orden ya fue abierta con el token válido en su momento.
        Cerrarla con un token vencido es de bajo riesgo. Lo que NO
        aceptamos es un token completamente falso o de otro restaurante.
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token requerido para operaciones POS",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_service = TokenService()

    try:
        # Primero intentar decode normal (token vigente)
        payload = token_service.decode_token(token)
    except Exception:
        try:
            # Si venció, decodificar ignorando expiración (preserva continuidad POS)
            payload = token_service.decode_token_ignore_expiry(token)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Token con firma inválida: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"},
            )

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token sin identidad de usuario",
        )

    return {
        "id": int(user_id),
        "username": payload.get("username"),
        "nombre_completo": payload.get("nombre_completo"),
        "rol": payload.get("rol") or "mesero",
        "restaurante_id": payload.get("restaurante_id"),
    }


def require_role(*roles: RolEnum):
    """Dependencia para restringir acceso por rol."""
    def dependency(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        if user.get("rol") not in [r.value for r in roles]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permiso denegado")
        return user

    return Depends(dependency)


async def require_superadmin(
    x_superadmin_key: str | None = None,
) -> None:
    """
    CONCEPTO: Operaciones de control plane (crear/listar restaurantes).

    El superadmin no es un usuario en ningún DB de tenant — es una clave
    de API configurada en las variables de entorno del servidor.
    Esto evita que un administrador de Restaurante A pueda crear
    o ver los restaurantes B, C, D...

    En Railway: configura SUPERADMIN_API_KEY como variable de entorno secreta.
    En local: ponla en .env.

    Uso: pasar el header X-Superadmin-Key: <clave> en las requests.
    """
    from fastapi import Header
    from app.config import settings

    if not settings.superadmin_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SUPERADMIN_API_KEY no configurada en el servidor",
        )
    if x_superadmin_key != settings.superadmin_api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Clave de superadmin inválida",
        )
