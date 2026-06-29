from __future__ import annotations
from decimal import Decimal
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, date, time


class MesaStatusDTO(BaseModel):
    """DTO para estado actual de una mesa (desde v_mesas_estado)"""
    id: int
    numero: str = Field(..., example="1")
    capacidad: int = Field(default=4)
    zona: Optional[str] = Field(None, example="Interior")
    estado: str = Field(..., example="libre")  # libre, ocupada, reservada, en_espera_cuenta
    orden_id: Optional[int] = None
    num_comensales: Optional[int] = None
    hora_apertura: Optional[datetime] = None
    mesero: Optional[str] = Field(None, example="Juan")
    total_neto: Optional[Decimal] = None

    class Config:
        from_attributes = True


class MesaMapResponseDTO(BaseModel):
    """Respuesta para mapa de mesas agrupado por zona"""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    mapa: dict[str, list[MesaStatusDTO]]  # zona -> lista de mesas
    total_mesas: int
    ocupadas: int
    reservadas: int
    libres: int


class MesaListResponseDTO(BaseModel):
    """Respuesta para listar todas las mesas"""
    mesas: list[MesaStatusDTO]
    total: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AbrirMesaRequestDTO(BaseModel):
    """DTO para solicitud de apertura de mesa (RF-06)"""
    num_comensales: int = Field(..., gt=0, le=100, example=4, description="Número de personas (1-100)")

    class Config:
        from_attributes = True


class AbrirMesaResponseDTO(BaseModel):
    """DTO respuesta al abrir una mesa (RF-06)"""
    mesa_id: int
    mesa_numero: str
    orden_id: int
    mesero_id: int
    mesero_nombre: str
    num_comensales: int
    hora_apertura: datetime
    estado_mesa: str
    mensaje: str = "Mesa abierta exitosamente"

    class Config:
        from_attributes = True


class ReservarMesaRequestDTO(BaseModel):
    """DTO para solicitud de reserva de mesa (RF-08)"""
    nombre_cliente: str = Field(..., example="Juan Pérez")
    telefono_cliente: Optional[str] = Field(None, example="3001234567")
    fecha_reserva: date = Field(..., example="2026-06-01")
    hora_reserva: time = Field(..., example="19:00:00")
    num_personas: int = Field(..., gt=0, le=100, example=4)
    notas: Optional[str] = Field(None, example="Mesa junto a la ventana")

    class Config:
        from_attributes = True


class ReservarMesasRequestDTO(ReservarMesaRequestDTO):
    """DTO para solicitud de reserva de una o varias mesas"""
    mesa_ids: list[int] = Field(..., min_items=1, example=[1, 2])

    class Config:
        from_attributes = True


class ReservarMesaResponseDTO(BaseModel):
    """DTO respuesta al reservar una mesa"""
    reserva_id: int
    mesa_id: int
    mesa_numero: str
    nombre_cliente: str
    telefono_cliente: Optional[str] = None
    fecha_reserva: date
    hora_reserva: time
    num_personas: int
    estado_reserva: str
    mensaje: str

    class Config:
        from_attributes = True


class ReservarMesasResponseDTO(BaseModel):
    """DTO respuesta al reservar una o varias mesas"""
    reservas: list[ReservarMesaResponseDTO]
    total_reservas: int
    mensaje: str

    class Config:
        from_attributes = True
