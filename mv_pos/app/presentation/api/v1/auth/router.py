from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.presentation.schemas.auth import LoginRequest, LoginResponse, ErrorResponse
from app.presentation.dependencies.auth_deps import get_token_service
from app.presentation.dependencies.db_deps import get_db_session
from app.domain.use_cases.authenticate_user import AutenticarUsuario
from app.domain.exceptions.auth_exceptions import InvalidCredentialsException, AccountLockedException
from app.infrastructure.database.models.restaurante import RestauranteORM
from app.infrastructure.repositories.usuario_repo_sqlalchemy import UsuarioRepoSQLAlchemy

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/login",
    response_model=LoginResponse,
    responses={
        401: {"model": ErrorResponse},
        423: {"model": ErrorResponse},
    },
)
async def login(
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db_session),
    token_service=Depends(get_token_service),
) -> LoginResponse:
    """
    Login multi-tenant en 2 pasos (shared DB).

    PASO 1 — Resolver tenant:
        Buscamos el slug en la tabla "restaurantes" del DB compartido.
        Si no existe → 401 (no revelamos si es el slug o la clave lo incorrecto).

    PASO 2 — Autenticar:
        UsuarioRepoSQLAlchemy filtra por restaurante_id automáticamente.
        Verificamos username + password dentro del tenant correcto.
        JWT resultante incluye restaurante_id para requests futuros.
    """

    # ── PASO 1: Resolver tenant ────────────────────────────────────────────────
    result = await db.execute(
        select(RestauranteORM).where(
            RestauranteORM.slug == payload.tenant_slug,
            RestauranteORM.activo == True,
        )
    )
    restaurante = result.scalar_one_or_none()

    if restaurante is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas",
        )

    # ── PASO 2: Autenticar en el tenant ───────────────────────────────────────
    try:
        usuario_repo = UsuarioRepoSQLAlchemy(db, restaurante.id)
        use_case = AutenticarUsuario(usuario_repo)

        user, expires, tokens = await use_case.execute(
            username=payload.username,
            password=payload.password,
            remember_me=payload.remember_me,
            token_service=token_service,
            restaurante_id=restaurante.id,
        )

    except InvalidCredentialsException:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas",
        )
    except AccountLockedException as e:
        raise HTTPException(status_code=423, detail=str(e))

    return LoginResponse(
        access_token=tokens["access_token"],
        expires_in=expires,
        refresh_token=tokens.get("refresh_token"),
        user={
            "id": user.id,
            "nombre_completo": user.nombre_completo,
            "username": user.username,
            "rol": getattr(user.rol, "nombre", None) if user.rol else None,
            "restaurante_id": restaurante.id,
        },
        restaurante_slug=restaurante.slug,
    )
