from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional, Tuple

from app.domain.repositories.usuario_repository import UsuarioRepository
from app.domain.exceptions.auth_exceptions import InvalidCredentialsException, AccountLockedException
from app.infrastructure.security.password import verify_password


class AutenticarUsuario:
    def __init__(self, usuario_repo: UsuarioRepository):
        self.usuario_repo = usuario_repo

    async def execute(
        self,
        username: str,
        password: str,
        remember_me: bool,
        token_service,
        restaurante_id: Optional[int] = None,
    ) -> Tuple[object, int, dict]:
        """
        CONCEPTO: Autenticación con contexto de tenant.

        El restaurante_id se recibe desde el router de login, que ya
        resolvió el slug → restaurante_id consultando el control DB.

        Se pasa al token_service.create_tokens() para que quede grabado
        en el JWT. Así cada token lleva su "pasaporte" de tenant.

        Sin este campo en el JWT, todos los requests posteriores
        irían al DB default en lugar del DB del restaurante correcto.
        """
        usuario = await self.usuario_repo.obtener_por_username(username)

        if usuario is None:
            raise InvalidCredentialsException()

        if getattr(usuario, "bloqueado", False):
            raise AccountLockedException("Cuenta bloqueada temporalmente")

        if not verify_password(password, usuario.password_hash):
            raise InvalidCredentialsException()

        ahora = datetime.utcnow()
        access_ttl = int(token_service.access_expires_seconds)
        sesion_expira = ahora + timedelta(seconds=access_ttl)
        await self.usuario_repo.actualizar_sesion(usuario.id, sesion_expira, ahora)

        tokens = token_service.create_tokens(
            sub=str(usuario.id),
            rol=getattr(usuario.rol, "nombre", None),
            username=usuario.username,
            nombre_completo=usuario.nombre_completo,
            restaurante_id=restaurante_id,
            remember_me=remember_me,
        )

        return usuario, access_ttl, tokens
