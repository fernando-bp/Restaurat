from __future__ import annotations
from abc import ABC, abstractmethod

from app.domain.entities.rol import Rol

class RolRepository(ABC):
    @abstractmethod
    async def obtener_por_id(self, rol_id: int) -> Rol | None:
        raise NotImplementedError

    @abstractmethod
    async def listar(self) -> list[Rol]:
        raise NotImplementedError

    @abstractmethod
    async def guardar(self, rol: Rol) -> Rol:
        raise NotImplementedError

    @abstractmethod
    async def eliminar(self, rol_id: int) -> None:
        raise NotImplementedError
