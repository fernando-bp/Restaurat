from __future__ import annotations
from abc import ABC, abstractmethod

from app.domain.entities.pago import Pago

class PagoRepository(ABC):
    @abstractmethod
    async def obtener_por_id(self, pago_id: int) -> Pago | None:
        raise NotImplementedError

    @abstractmethod
    async def listar_por_orden(self, orden_id: int) -> list[Pago]:
        raise NotImplementedError

    @abstractmethod
    async def guardar(self, pago: Pago) -> Pago:
        raise NotImplementedError
