from __future__ import annotations
from abc import ABC, abstractmethod

from app.domain.entities.orden_item import OrdenItem


class OrdenItemRepository(ABC):
    @abstractmethod
    async def obtener_por_id(self, orden_item_id: int) -> OrdenItem | None:
        raise NotImplementedError

    @abstractmethod
    async def listar_por_orden(self, orden_id: int) -> list[OrdenItem]:
        raise NotImplementedError

    @abstractmethod
    async def guardar(self, orden_item: OrdenItem) -> OrdenItem:
        raise NotImplementedError

    @abstractmethod
    async def eliminar(self, orden_item_id: int) -> None:
        raise NotImplementedError
