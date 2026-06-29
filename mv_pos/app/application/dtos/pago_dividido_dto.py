from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class CrearPagoDivididoRequest(BaseModel):
    """Request para crear una división de pago"""
    orden_id: int
    numero_personas: int
    monto_total: Decimal
    montos_personas: Optional[List[Decimal]] = None


class PersonaPagoDivididoDTO(BaseModel):
    """DTO para una persona en el pago dividido"""
    numero_persona: int
    monto: Decimal
    pagado: bool = False
    forma_pago: Optional[str] = None
    monto_recibido: Optional[Decimal] = None
    cambio_entregado: Optional[Decimal] = None
    pagado_at: Optional[datetime] = None


class PagoDivididoResumenDTO(BaseModel):
    """Resumen de un pago dividido"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    orden_id: int
    numero_personas: int
    monto_total: Decimal
    monto_por_persona: Decimal
    personas_pagadas: int
    completado: bool
    created_at: datetime
    personas: List[PersonaPagoDivididoDTO]


class RegistrarPagoPersonaRequest(BaseModel):
    """Request para registrar el pago de una persona"""
    numero_persona: int
    forma_pago: str
    monto_recibido: Optional[Decimal] = None
    referencia_datafono: Optional[str] = None
    numero_comprobante: Optional[str] = None


class RegistrarPagoPersonaResponse(BaseModel):
    """Response del pago de una persona"""
    numero_persona: int
    monto: Decimal
    forma_pago: str
    cambio_entregado: Optional[Decimal] = None
    pagado_at: Optional[datetime] = None
    completado_division: bool = False
