from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from app.domain.enums.forma_pago import FormaPagoEnum


@dataclass
class Pago:
    """Entidad de dominio para Pagos (RF-27 a RF-34)
    
    Soporta:
    - RF-27: Generar cuenta detallada
    - RF-28: Pago en efectivo con cálculo de cambio
    - RF-29: Pago con tarjeta (referencia datafono obligatoria)
    - RF-30: Pago por transferencia (comprobante obligatorio)
    - RF-31: Pago mixto (múltiples formas)
    - RF-33: Autorización de descuentos > 10%
    - RF-34: Cierre de caja diario
    """
    
    id: int | None
    orden_id: int
    forma_pago: FormaPagoEnum
    monto: Decimal  # Monto pagado en esta transacción
    monto_recibido: Decimal | None = None  # Solo para efectivo
    cambio_entregado: Decimal | None = None  # Solo para efectivo
    referencia_datafono: str | None = None  # Obligatorio para tarjeta (RF-29)
    numero_comprobante: str | None = None  # Obligatorio para transferencia (RF-30)
    cajero_id: int | None = None
    created_at: datetime | None = None

    def validar_efectivo(self) -> None:
        """Valida pago en efectivo: monto_recibido debe ser >= monto (RF-28)"""
        if self.forma_pago == FormaPagoEnum.EFECTIVO:
            if self.monto_recibido is None:
                raise ValueError("monto_recibido es requerido para pago en efectivo")
            if self.monto_recibido < self.monto:
                raise ValueError("monto_recibido debe ser mayor o igual al monto")

    def validar_tarjeta(self) -> None:
        """Valida pago con tarjeta: requiere referencia de datafono (RF-29)"""
        if self.forma_pago in (FormaPagoEnum.TARJETA_DEBITO, FormaPagoEnum.TARJETA_CREDITO):
            if not self.referencia_datafono:
                raise ValueError(f"referencia_datafono es obligatoria para {self.forma_pago.value}")

    def validar_transferencia(self) -> None:
        """Valida pago por transferencia: requiere número de comprobante (RF-30)"""
        if self.forma_pago in (FormaPagoEnum.NEQUI, FormaPagoEnum.DAVIPLATA, FormaPagoEnum.PSE, FormaPagoEnum.QR_BREB):
            if not self.numero_comprobante:
                raise ValueError(f"numero_comprobante es obligatorio para {self.forma_pago.value}")

    def validar(self) -> None:
        """Valida todas las restricciones del pago"""
        self.validar_efectivo()
        self.validar_tarjeta()
        self.validar_transferencia()

    def calcular_cambio(self) -> Decimal:
        """Calcula el cambio en pago en efectivo (RF-28)"""
        if self.forma_pago != FormaPagoEnum.EFECTIVO:
            return Decimal(0)
        if self.monto_recibido is None:
            return Decimal(0)
        return self.monto_recibido - self.monto

    def registrar(self) -> None:
        """Registra el pago validando todas las restricciones"""
        if self.monto <= 0:
            raise ValueError("El monto de pago debe ser mayor que cero")
        if self.fecha is None:
            self.created_at = datetime.utcnow()
        self.validar()
