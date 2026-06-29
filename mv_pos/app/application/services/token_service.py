from __future__ import annotations
from datetime import datetime, timedelta
from typing import Dict, Any

from jose import jwt, JWTError

from app.config import settings


class TokenService:
    def __init__(self, secret: str | None = None, algorithm: str | None = None, access_expires_seconds: int | None = None, refresh_expires_seconds: int | None = None):
        self.secret = secret or settings.secret_key
        self.algorithm = algorithm or settings.algorithm
        self.access_expires_seconds = access_expires_seconds or settings.access_token_expire_minutes * 60
        self.refresh_expires_seconds = refresh_expires_seconds or 86400

    def _now(self) -> datetime:
        return datetime.utcnow()

    def create_access_token(self, sub: str, rol: str | None = None, username: str | None = None, nombre_completo: str | None = None, expires_seconds: int | None = None) -> str:
        expires = self._now() + timedelta(seconds=expires_seconds or self.access_expires_seconds)
        payload = {"sub": sub, "iat": int(self._now().timestamp()), "exp": int(expires.timestamp())}
        if rol:
            payload["rol"] = rol
        if username:
            payload["username"] = username
        if nombre_completo:
            payload["nombre_completo"] = nombre_completo
        return jwt.encode(payload, self.secret, algorithm=self.algorithm)

    def create_refresh_token(self, sub: str, expires_seconds: int | None = None) -> str:
        expires = self._now() + timedelta(seconds=expires_seconds or self.refresh_expires_seconds)
        payload = {"sub": sub, "iat": int(self._now().timestamp()), "exp": int(expires.timestamp())}
        return jwt.encode(payload, self.secret, algorithm=self.algorithm)

    def create_tokens(self, sub: str, rol: str | None = None, username: str | None = None, nombre_completo: str | None = None, remember_me: bool = False) -> Dict[str, str]:
        access = self.create_access_token(sub=sub, rol=rol, username=username, nombre_completo=nombre_completo)
        refresh = None
        if remember_me:
            refresh = self.create_refresh_token(sub=sub)
        return {"access_token": access, "refresh_token": refresh}

    def decode_token(self, token: str) -> Dict[str, Any]:
        """Decodifica y valida un token JWT.
        
        Args:
            token: Token JWT a decodificar
            
        Returns:
            Payload del token con los claims
            
        Raises:
            JWTError: Si el token es inválido o está expirado
        """
        try:
            payload = jwt.decode(token, self.secret, algorithms=[self.algorithm])
            return payload
        except JWTError as e:
            raise JWTError(f"Token inválido o expirado: {str(e)}")
