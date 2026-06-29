from __future__ import annotations
from abc import ABC, abstractmethod

from app.domain.entities.descuento import Descuento


class DescuentoRepository(ABC):
    @abstractmethod
    async def obtener_por_id(self, descuento_id: int) -> Descuento | None:
        raise NotImplementedError

    @abstractmethod
    async def listar_por_orden(self, orden_id: int) -> list[Descuento]:
        raise NotImplementedError

    @abstractmethod
    async def guardar(self, descuento: Descuento) -> Descuento:
        raise NotImplementedError
