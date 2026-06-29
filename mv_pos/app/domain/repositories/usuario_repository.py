from __future__ import annotations
from abc import ABC, abstractmethod

from app.domain.entities.usuario import Usuario

class UsuarioRepository(ABC):
    @abstractmethod
    async def agregar(self, usuario: Usuario) -> Usuario:
        raise NotImplementedError

    @abstractmethod
    async def obtener_por_id(self, usuario_id: int) -> Usuario | None:
        raise NotImplementedError

    @abstractmethod
    async def obtener_por_username(self, username: str) -> Usuario | None:
        raise NotImplementedError

    @abstractmethod
    async def actualizar_sesion(self, usuario_id: int, sesion_expira, ultimo_acceso) -> None:
        raise NotImplementedError

    @abstractmethod
    async def listar(self) -> list[Usuario]:
        raise NotImplementedError
