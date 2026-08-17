from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from jose import jwt, JWTError

from app.config import settings


class TokenService:
    def __init__(
        self,
        secret: str | None = None,
        algorithm: str | None = None,
        access_expires_seconds: int | None = None,
        refresh_expires_seconds: int | None = None,
    ):
        self.secret = secret or settings.secret_key
        self.algorithm = algorithm or settings.algorithm
        self.access_expires_seconds = access_expires_seconds or settings.access_token_expire_minutes * 60
        self.refresh_expires_seconds = refresh_expires_seconds or 86400

    def _now(self) -> datetime:
        return datetime.utcnow()

    def create_access_token(
        self,
        sub: str,
        rol: str | None = None,
        username: str | None = None,
        nombre_completo: str | None = None,
        restaurante_id: int | None = None,
        expires_seconds: int | None = None,
    ) -> str:
        """
        CONCEPTO: El JWT como pasaporte del usuario.

        Un JWT (JSON Web Token) tiene tres partes: header.payload.signature
        El payload contiene "claims" — datos que el servidor firmó digitalmente.

        Claims estándar:
          sub  → "subject" = identificador del usuario (su ID en la DB)
          iat  → "issued at" = cuándo se creó
          exp  → "expires" = cuándo vence

        Claims propios:
          rol              → permisos del usuario
          username         → nombre de usuario
          nombre_completo  → nombre para mostrar en UI
          restaurante_id   → ← NUEVO: a qué restaurante pertenece

        El restaurante_id es lo que permite al server saber a qué DB
        conectarse en cada request SIN consultar la DB de control.
        Es O(1): solo un dict lookup en tenant_registry.
        """
        expires = self._now() + timedelta(seconds=expires_seconds or self.access_expires_seconds)
        payload: Dict[str, Any] = {
            "sub": sub,
            "iat": int(self._now().timestamp()),
            "exp": int(expires.timestamp()),
        }
        if rol:
            payload["rol"] = rol
        if username:
            payload["username"] = username
        if nombre_completo:
            payload["nombre_completo"] = nombre_completo
        if restaurante_id is not None:
            payload["restaurante_id"] = restaurante_id
        return jwt.encode(payload, self.secret, algorithm=self.algorithm)

    def create_refresh_token(self, sub: str, expires_seconds: int | None = None) -> str:
        expires = self._now() + timedelta(seconds=expires_seconds or self.refresh_expires_seconds)
        payload = {
            "sub": sub,
            "iat": int(self._now().timestamp()),
            "exp": int(expires.timestamp()),
        }
        return jwt.encode(payload, self.secret, algorithm=self.algorithm)

    def create_tokens(
        self,
        sub: str,
        rol: str | None = None,
        username: str | None = None,
        nombre_completo: str | None = None,
        restaurante_id: int | None = None,
        remember_me: bool = False,
    ) -> Dict[str, str | None]:
        access = self.create_access_token(
            sub=sub,
            rol=rol,
            username=username,
            nombre_completo=nombre_completo,
            restaurante_id=restaurante_id,
        )
        refresh = self.create_refresh_token(sub=sub) if remember_me else None
        return {"access_token": access, "refresh_token": refresh}

    def decode_token(self, token: str) -> Dict[str, Any]:
        """
        Decodifica y verifica firma + expiración del token.

        Raises JWTError si el token es inválido o está expirado.
        """
        try:
            return jwt.decode(token, self.secret, algorithms=[self.algorithm])
        except JWTError as e:
            raise JWTError(f"Token inválido o expirado: {str(e)}")

    def decode_token_ignore_expiry(self, token: str) -> Dict[str, Any]:
        """
        Decodifica el token sin verificar expiración.

        CUÁNDO USARLO: flujo POS donde queremos mantener la sesión
        activa aunque el token esté vencido (ver get_current_pos_user).
        Solo verifica la firma, no el tiempo de vida.

        NUNCA usar para operaciones sensibles (pagos, cierre de caja, etc.)
        """
        try:
            return jwt.decode(
                token,
                self.secret,
                algorithms=[self.algorithm],
                options={"verify_exp": False},
            )
        except JWTError as e:
            raise JWTError(f"Token con firma inválida: {str(e)}")
