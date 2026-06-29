from __future__ import annotations
from abc import ABC, abstractmethod

from app.domain.entities.ingrediente import Ingrediente

class IngredienteRepository(ABC):
    @abstractmethod
    async def obtener_por_id(self, ingrediente_id: int) -> Ingrediente | None:
        raise NotImplementedError

    @abstractmethod
    async def listar(self, disponibles: bool | None = None) -> list[Ingrediente]:
        raise NotImplementedError

    @abstractmethod
    async def guardar(self, ingrediente: Ingrediente) -> Ingrediente:
        raise NotImplementedError

    @abstractmethod
    async def eliminar(self, ingrediente_id: int) -> None:
        raise NotImplementedError
