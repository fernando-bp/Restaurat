from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime


class BilleteMonedaDTO(BaseModel):
    """DTO para billete o moneda individual."""
    denominacion: float = Field(..., gt=0, description="Denominación del billete/moneda")
    cantidad: int = Field(..., ge=0, description="Cantidad de billetes/monedas")


class ConteoEfectivoDTO(BaseModel):
    """DTO para conteo físico de efectivo."""
    billetes: List[BilleteMonedaDTO] = Field(..., description="Lista de billetes")
    monedas: List[BilleteMonedaDTO] = Field(..., description="Lista de monedas")
    
    def calcular_total(self) -> float:
        """Calcula el total del efectivo contado."""
        total_billetes = sum(b.denominacion * b.cantidad for b in self.billetes)
        total_monedas = sum(m.denominacion * m.cantidad for m in self.monedas)
        return total_billetes + total_monedas


class ResumenPagoDTO(BaseModel):
    """Resumen de pagos por forma de pago."""
    forma_pago: str
    total: float
    cantidad_transacciones: int


class CierreCajaResumenDTO(BaseModel):
    """Resumen previo al cierre (antes de contar efectivo)."""
    fecha: str
    total_ventas: float
    por_forma_pago: List[ResumenPagoDTO]
    total_efectivo_sistema: float
    total_tarjeta_debito: float
    total_tarjeta_credito: float
    total_transferencia: float
    total_cortesia: float
    total_descuentos: float


class CierreCajaRequestDTO(BaseModel):
    """Request para cierre de caja con conteo de efectivo."""
    efectivo_contado: ConteoEfectivoDTO = Field(..., description="Conteo físico del efectivo")
    observaciones: Optional[str] = Field(None, max_length=500, description="Observaciones del cierre")


class CierreCajaResponseDTO(BaseModel):
    """Response después del cierre de caja."""
    id: int
    fecha: str
    
    # Totales por forma de pago
    total_efectivo_sistema: float
    total_efectivo_contado: float
    total_tarjeta_debito: float
    total_tarjeta_credito: float
    total_transferencia: float
    total_cortesia: float
    total_descuentos: float
    total_ventas: float
    
    # Cuadre
    diferencia_efectivo: float
    diferencia_porcentaje: Optional[float] = None
    cuadra: bool
    
    # Observaciones
    observaciones: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class ImpresionCierreCajaDTO(BaseModel):
    """DTO para impresión del cierre de caja."""
    titulo: str = "CIERRE DE CAJA DIARIO"
    fecha: str
    horario: str
    
    # Resumen de ingresos
    resumen_ingresos: Dict[str, float]
    
    # Detalle de efectivo
    detalle_efectivo: str
    total_efectivo_sistema: float
    total_efectivo_contado: float
    diferencia_efectivo: float
    
    # Estado
    estado: str  # "CUADRADO", "DIFERENCIA POSITIVA", "DIFERENCIA NEGATIVA"
    observaciones: Optional[str]
    
    # Firma
    cajero: str
    autorizado_por: Optional[str] = None
