from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, status

from app.presentation.schemas.auth import LoginRequest, LoginResponse, ErrorResponse
from app.presentation.dependencies.auth_deps import get_usuario_repository, get_token_service
from app.domain.use_cases.authenticate_user import AutenticarUsuario
from app.domain.exceptions.auth_exceptions import InvalidCredentialsException, AccountLockedException

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse, responses={401: {"model": ErrorResponse}, 423: {"model": ErrorResponse}})
async def login(payload: LoginRequest, usuario_repo=Depends(get_usuario_repository), token_service=Depends(get_token_service)) -> LoginResponse:
    use_case = AutenticarUsuario(usuario_repo)
    try:
        user, expires, refresh = await use_case.execute(
            username=payload.username,
            password=payload.password,
            remember_me=payload.remember_me,
            token_service=token_service,
        )
    except InvalidCredentialsException:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas")
    except AccountLockedException as e:
        raise HTTPException(status_code=423, detail=str(e))

    return LoginResponse(
        access_token=refresh["access_token"],
        expires_in=expires,
        refresh_token=refresh.get("refresh_token"),
        user={
            "id": user.id,
            "nombre_completo": user.nombre_completo,
            "username": user.username,
            "rol": getattr(user.rol, "nombre", None) if user.rol else None,
        },
    )
