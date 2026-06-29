from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import List

from app.domain.enums.estado_orden import EstadoOrdenEnum
from app.domain.entities.orden_item import OrdenItem
from app.domain.exceptions.orden_exceptions import TransicionEstadoInvalidaException

@dataclass
class Orden:
    id: int | None
    mesa_id: int
    mesero_id: int
    num_comensales: int
    estado: EstadoOrdenEnum
    items: List[OrdenItem] = field(default_factory=list)
    hora_apertura: datetime = field(default_factory=datetime.utcnow)
    notas_generales: str | None = None
    hora_confirmacion: datetime | None = None
    hora_cierre: datetime | None = None
    total_bruto: int = 0
    total_descuento: int = 0
    total_iva: int = 0
    total_neto: int = 0
    transferencia_a_mesero_id: int | None = None  # Para auditoría de transferencias

    def subtotal(self) -> int:
        return sum(item.subtotal() for item in self.items)

    def agregar_item(self, item: OrdenItem) -> None:
        if self.estado != EstadoOrdenEnum.ABIERTA:
            raise TransicionEstadoInvalidaException('Solo se puede agregar ítems en ordenes abiertas')
        self.items.append(item)

    def confirmar(self) -> None:
        if self.estado != EstadoOrdenEnum.ABIERTA:
            raise TransicionEstadoInvalidaException('Solo se puede confirmar una orden abierta')
        if not self.items:
            raise ValueError('Orden debe tener al menos un ítem para confirmar')
        self.estado = EstadoOrdenEnum.EN_PREPARACION
