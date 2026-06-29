from __future__ import annotations
from abc import ABC, abstractmethod

from app.domain.entities.reserva import Reserva

class ReservaRepository(ABC):
    @abstractmethod
    async def obtener_por_id(self, reserva_id: int) -> Reserva | None:
        raise NotImplementedError

    @abstractmethod
    async def obtener_activa_por_mesa(self, mesa_id: int) -> Reserva | None:
        raise NotImplementedError

    @abstractmethod
    async def guardar(self, reserva: Reserva) -> Reserva:
        raise NotImplementedError

    @abstractmethod
    async def cancelar(self, reserva_id: int) -> None:
        raise NotImplementedError
