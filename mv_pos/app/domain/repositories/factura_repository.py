from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.entities.factura import Factura


class FacturaRepository(ABC):
    @abstractmethod
    async def guardar(self, factura: Factura) -> Factura:
        raise NotImplementedError

    @abstractmethod
    async def obtener_por_id(self, factura_id: int) -> Factura | None:
        raise NotImplementedError

    @abstractmethod
    async def obtener_por_orden_id(self, orden_id: int) -> list[Factura]:
        raise NotImplementedError
