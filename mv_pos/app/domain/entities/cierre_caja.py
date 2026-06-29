from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass
class CierreCaja:
    """Entidad de dominio para Cierre de Caja Diario (RF-34)"""
    
    id: int | None
    fecha: str  # YYYY-MM-DD
    cajero_id: int
    autorizado_por: int | None = None
    total_ventas: Decimal = Decimal(0)
    total_efectivo_sistema: Decimal = Decimal(0)
    total_efectivo_contado: Decimal = Decimal(0)
    total_tarjeta: Decimal = Decimal(0)
    total_transferencia: Decimal = Decimal(0)
    total_cortesia: Decimal = Decimal(0)
    total_descuentos: Decimal = Decimal(0)
    observaciones: str | None = None
    firmado_at: datetime | None = None
    created_at: datetime | None = None

    @property
    def diferencia_efectivo(self) -> Decimal:
        """Diferencia entre efectivo contado vs sistema (RF-34)"""
        return self.total_efectivo_contado - self.total_efectivo_sistema

    @property
    def saldo_total(self) -> Decimal:
        """Total de dinero en caja: efectivo + tarjeta + transferencia"""
        return (
            self.total_efectivo_contado +
            self.total_tarjeta +
            self.total_transferencia
        )

    def validar_cierre(self) -> bool:
        """Valida que el cierre sea consistente"""
        # El total de ventas debe coincidir con la suma de formas de pago
        total_pagos = (
            self.total_efectivo_sistema +
            self.total_tarjeta +
            self.total_transferencia +
            self.total_cortesia
        )
        return (self.total_ventas - self.total_descuentos) == total_pagos
