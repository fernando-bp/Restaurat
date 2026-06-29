from __future__ import annotations
from dataclasses import dataclass

from app.domain.value_objects.money import Money

@dataclass
class Ingrediente:
    id: int | None
    nombre: str
    unidad_base_id: int
    precio_unitario: Money
    categoria: str | None
    activo: bool

    def actualizar_precio(self, nuevo_precio: Money) -> None:
        self.precio_unitario = nuevo_precio
