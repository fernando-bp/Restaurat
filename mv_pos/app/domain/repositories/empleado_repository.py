from __future__ import annotations
from abc import ABC, abstractmethod

from app.domain.entities.empleado import Empleado

class EmpleadoRepository(ABC):
    @abstractmethod
    async def obtener_por_id(self, empleado_id: int) -> Empleado | None:
        raise NotImplementedError

    @abstractmethod
    async def listar(self, estado: str | None = None) -> list[Empleado]:
        raise NotImplementedError

    @abstractmethod
    async def guardar(self, empleado: Empleado) -> Empleado:
        raise NotImplementedError

    @abstractmethod
    async def eliminar(self, empleado_id: int) -> None:
        raise NotImplementedError
