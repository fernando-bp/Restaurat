from __future__ import annotations
from abc import ABC, abstractmethod

from app.domain.entities.cierre_caja import CierreCaja


class CierreCajaRepository(ABC):
    @abstractmethod
    async def obtener_por_fecha(self, fecha: str) -> CierreCaja | None:
        raise NotImplementedError

    @abstractmethod
    async def guardar(self, cierre: CierreCaja) -> CierreCaja:
        raise NotImplementedError
