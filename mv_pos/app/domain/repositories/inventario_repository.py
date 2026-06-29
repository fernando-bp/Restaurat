from __future__ import annotations
from abc import ABC, abstractmethod

from app.domain.entities.inventario import Inventario

class InventarioRepository(ABC):
    @abstractmethod
    async def obtener_por_id(self, inventario_id: int) -> Inventario | None:
        raise NotImplementedError

    @abstractmethod
    async def obtener_por_ingrediente(self, ingrediente_id: int) -> Inventario | None:
        raise NotImplementedError

    @abstractmethod
    async def listar(self) -> list[Inventario]:
        raise NotImplementedError

    @abstractmethod
    async def guardar(self, inventario: Inventario) -> Inventario:
        raise NotImplementedError

    @abstractmethod
    async def eliminar(self, inventario_id: int) -> None:
        raise NotImplementedError
