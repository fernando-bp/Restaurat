from __future__ import annotations
from dataclasses import dataclass

@dataclass
class OrdenItem:
    id: int | None
    orden_id: int
    receta_id: int
    cantidad: int
    precio_unitario: int
    estado: str = 'pendiente'
    observaciones: str | None = None

    def subtotal(self) -> int:
        return self.cantidad * self.precio_unitario
