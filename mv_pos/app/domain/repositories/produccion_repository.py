from __future__ import annotations
from abc import ABC, abstractmethod

from app.domain.entities.produccion import Produccion

class ProduccionRepository(ABC):
    @abstractmethod
    async def obtener_por_id(self, produccion_id: int) -> Produccion | None:
        raise NotImplementedError

    @abstractmethod
    async def listar_pendientes(self) -> list[Produccion]:
        raise NotImplementedError

    @abstractmethod
    async def guardar(self, produccion: Produccion) -> Produccion:
        raise NotImplementedError
