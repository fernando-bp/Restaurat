from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Optional

from app.domain.entities.mesa import Mesa

class MesaRepository(ABC):
    @abstractmethod
    async def obtener_por_id(self, mesa_id: int) -> Mesa | None:
        raise NotImplementedError

    @abstractmethod
    async def listar(self) -> list[Mesa]:
        raise NotImplementedError

    @abstractmethod
    async def guardar(self, mesa: Mesa) -> Mesa:
        raise NotImplementedError

    @abstractmethod
    async def eliminar(self, mesa_id: int) -> None:
        raise NotImplementedError

    @abstractmethod
    async def obtener_estado_mesas(self, zona: Optional[str] = None) -> list[dict]:
        """Obtiene estado en tiempo real de mesas desde v_mesas_estado (RF-05)"""
        raise NotImplementedError

    @abstractmethod
    async def obtener_estado_mesa(self, mesa_id: int) -> dict | None:
        """Obtiene estado en tiempo real de una mesa específica (RF-05)"""
        raise NotImplementedError
