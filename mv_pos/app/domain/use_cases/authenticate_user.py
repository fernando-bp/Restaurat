from __future__ import annotations
from typing import Tuple
from datetime import datetime, timedelta

from app.domain.repositories.usuario_repository import UsuarioRepository
from app.domain.exceptions.auth_exceptions import InvalidCredentialsException, AccountLockedException
from app.infrastructure.security.password import verify_password


class AutenticarUsuario:
    def __init__(self, usuario_repo: UsuarioRepository):
        self.usuario_repo = usuario_repo

    async def execute(self, username: str, password: str, remember_me: bool, token_service) -> Tuple[object, int, dict]:
        usuario = await self.usuario_repo.obtener_por_username(username)

        if usuario is None:
            raise InvalidCredentialsException()

        if getattr(usuario, "bloqueado", False):
            raise AccountLockedException("Cuenta bloqueada temporalmente")

        if not verify_password(password, usuario.password_hash):
            raise InvalidCredentialsException()

        ahora = datetime.utcnow()
        sesion_expira = ahora + timedelta(minutes=30)
        await self.usuario_repo.actualizar_sesion(usuario.id, sesion_expira, ahora)

        access_ttl = int(token_service.access_expires_seconds)
        tokens = token_service.create_tokens(
            sub=str(usuario.id), 
            rol=getattr(usuario.rol, "nombre", None), 
            username=usuario.username,
            nombre_completo=usuario.nombre_completo,
            remember_me=remember_me
        )

        return usuario, access_ttl, tokens
