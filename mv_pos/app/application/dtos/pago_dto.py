from __future__ import annotations
from datetime import datetime
from typing import List, Optional
from decimal import Decimal

from pydantic import BaseModel, Field, validator


class PagoRequestDTO(BaseModel):
    """DTO para registrar un pago (RF-27 a RF-34)"""
    
    orden_id: int = Field(..., gt=0)
    forma_pago: str = Field(..., example="efectivo")  # efectivo, tarjeta_debito, etc.
    monto: Decimal = Field(..., gt=0, example="50000")
    monto_recibido: Optional[Decimal] = Field(None, ge=0, example="50000")  # Solo efectivo
    referencia_datafono: Optional[str] = Field(None, example="123456789")  # Solo tarjeta (RF-29)
    numero_comprobante: Optional[str] = Field(None, example="TRF001234")  # Solo transferencia (RF-30)

    @validator("forma_pago")
    def validar_forma_pago(cls, v):
        formas_validas = [
            "efectivo", "tarjeta_debito", "tarjeta_credito",
            "nequi", "daviplata", "pse", "qr_breb", "cortesia"
        ]
        if v not in formas_validas:
            raise ValueError(f"forma_pago debe ser uno de: {', '.join(formas_validas)}")
        return v

    class Config:
        from_attributes = True


class PagoResponseDTO(BaseModel):
    """DTO de respuesta para Pago"""
    
    id: int
    orden_id: int
    forma_pago: str
    monto: Decimal
    monto_recibido: Optional[Decimal]
    cambio_entregado: Optional[Decimal]
    referencia_datafono: Optional[str]
    numero_comprobante: Optional[str]
    cajero_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class PagoParcialRequestDTO(BaseModel):
    """DTO para un pago parcial dentro de un pago mixto."""

    forma_pago: str = Field(..., example="efectivo")
    monto: Decimal = Field(..., gt=0, example="20000")
    monto_recibido: Optional[Decimal] = Field(None, ge=0, example="20000")
    referencia_datafono: Optional[str] = Field(None, example="123456789")
    numero_comprobante: Optional[str] = Field(None, example="TRF001234")

    @validator("forma_pago")
    def validar_forma_pago(cls, v):
        formas_validas = [
            "efectivo", "tarjeta_debito", "tarjeta_credito",
            "nequi", "daviplata", "pse", "qr_breb", "cortesia"
        ]
        if v not in formas_validas:
            raise ValueError(f"forma_pago debe ser uno de: {', '.join(formas_validas)}")
        return v

    class Config:
        from_attributes = True


class PagoMixtoRequestDTO(BaseModel):
    """DTO para pago mixto: múltiples formas de pago (RF-31)"""
    
    orden_id: int = Field(..., gt=0)
    pagos: List[PagoParcialRequestDTO] = Field(..., min_items=2, example=[
        {
            "forma_pago": "efectivo",
            "monto": 30000,
            "monto_recibido": 30000
        },
        {
            "forma_pago": "nequi",
            "monto": 20000,
            "numero_comprobante": "TRF001234"
        }
    ])

    @validator("pagos")
    def validar_suma_pagos(cls, v, values):
        """La suma de pagos parciales debe igualar el total (RF-31)"""
        if len(v) < 2:
            raise ValueError("Pago mixto requiere al menos 2 formas de pago")
        return v

    class Config:
        from_attributes = True


class CuentaDetalladadRequestDTO(BaseModel):
    """DTO para generar la cuenta detallada (RF-27)"""
    
    orden_id: int = Field(..., gt=0)
    incluir_descuentos: bool = Field(True)

    class Config:
        from_attributes = True


class CuentaDetalladaResponseDTO(BaseModel):
    """DTO de respuesta para cuenta detallada (RF-27)"""
    
    orden_id: int
    mesa_numero: str
    num_comensales: int
    items: List[dict]  # [{"receta": "...", "cantidad": 2, "precio_unitario": 10000, "subtotal": 20000}]
    total_bruto: Decimal
    descuentos_aplicados: List[dict]  # [{"motivo": "...", "porcentaje": 10, "monto": 5000}]
    total_descuento: Decimal
    iva: Decimal
    total_neto: Decimal
    fecha_apertura: datetime

    class Config:
        from_attributes = True


class CambioResponseDTO(BaseModel):
    """DTO para respuesta de cálculo de cambio (RF-28)"""
    
    monto_pagado: Decimal
    monto_adeudado: Decimal
    cambio: Decimal

    class Config:
        from_attributes = True


class DividirCuentaRequestDTO(BaseModel):
    """DTO para dividir la cuenta (RF-32)"""
    
    orden_id: int = Field(..., gt=0)
    tipo_division: str = Field(..., example="equitativa")  # equitativa, por_items
    num_formas: int = Field(..., gt=1, example=2)  # Número de divisiones

    class Config:
        from_attributes = True


class CierreCajaRequestDTO(BaseModel):
    """DTO para registrar cierre de caja (RF-34)"""
    
    fecha: str = Field(..., example="2026-06-08")  # YYYY-MM-DD
    total_efectivo_contado: Decimal = Field(..., ge=0)
    observaciones: Optional[str] = None

    class Config:
        from_attributes = True


class CierreCajaResponseDTO(BaseModel):
    """DTO de respuesta para cierre de caja (RF-34)"""
    
    id: int
    fecha: str
    cajero_id: int
    total_ventas: Decimal
    total_efectivo_sistema: Decimal
    total_efectivo_contado: Decimal
    diferencia_efectivo: Decimal
    total_tarjeta: Decimal
    total_transferencia: Decimal
    total_cortesia: Decimal
    total_descuentos: Decimal
    observaciones: Optional[str]
    firmado_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class DescuentoRequestDTO(BaseModel):
    """DTO para aplicar descuento o cortesía (RF-33)"""
    
    orden_id: int = Field(..., gt=0)
    porcentaje: Decimal = Field(..., gt=0, le=100, example="10.5")
    motivo: str = Field(..., example="Cliente VIP", min_length=3)
    pin_administrador: Optional[str] = None  # Requerido si porcentaje > 10

    class Config:
        from_attributes = True
