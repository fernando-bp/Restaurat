from __future__ import annotations
from abc import ABC, abstractmethod

from app.domain.entities.receta import Receta

class RecetaRepository(ABC):
    @abstractmethod
    async def obtener_por_id(self, receta_id: int) -> Receta | None:
        raise NotImplementedError

    @abstractmethod
    async def listar(self, activa: bool | None = None) -> list[Receta]:
        raise NotImplementedError

    @abstractmethod
    async def guardar(self, receta: Receta) -> Receta:
        raise NotImplementedError

    @abstractmethod
    async def explotar_bom(self, receta_id: int, porciones: int) -> dict[int, float]:
        raise NotImplementedError

    @abstractmethod
    async def eliminar(self, receta_id: int) -> None:
        raise NotImplementedError
