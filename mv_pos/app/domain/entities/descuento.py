from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass
class Descuento:
    id: int | None
    orden_id: int
    porcentaje: Decimal
    monto: Decimal
    motivo: str
    autorizado_por: int | None = None
    requirio_pin: bool = False
    created_at: datetime | None = None

    def validar(self) -> None:
        if self.porcentaje <= 0 or self.porcentaje > 100:
            raise ValueError("El porcentaje debe estar entre 0 y 100")
        if self.monto <= 0:
            raise ValueError("El monto del descuento debe ser mayor que cero")
        if not self.motivo or len(self.motivo.strip()) < 3:
            raise ValueError("El motivo del descuento debe tener al menos 3 caracteres")
