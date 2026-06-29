from __future__ import annotations
from abc import ABC, abstractmethod

from app.domain.entities.orden import Orden

class OrdenRepository(ABC):
    @abstractmethod
    async def obtener_por_id(self, orden_id: int) -> Orden | None:
        raise NotImplementedError

    @abstractmethod
    async def listar_por_mesa(self, mesa_id: int) -> list[Orden]:
        raise NotImplementedError

    @abstractmethod
    async def obtener_orden_activa_por_mesa(self, mesa_id: int) -> Orden | None:
        """Obtiene la única orden activa de una mesa (no pagada ni cancelada)"""
        raise NotImplementedError

    @abstractmethod
    async def guardar(self, orden: Orden) -> Orden:
        raise NotImplementedError

    @abstractmethod
    async def eliminar(self, orden_id: int) -> None:
        raise NotImplementedError

