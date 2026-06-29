from __future__ import annotations
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class OrdenItemCreateDTO(BaseModel):
    receta_id: int = Field(..., gt=0)
    cantidad: int = Field(..., gt=0)
    precio_unitario: Optional[int] = Field(None, ge=0, example=10000)
    notas: Optional[str] = Field(None, example="Sin cebolla")

    class Config:
        from_attributes = True


class CrearOrdenRequestDTO(BaseModel):
    mesa_id: int = Field(..., gt=0)
    num_comensales: int = Field(..., gt=0)
    notas_generales: Optional[str] = None
    items: Optional[List[OrdenItemCreateDTO]] = None

    class Config:
        from_attributes = True


class OrdenItemUpdateDTO(BaseModel):
    cantidad: int = Field(..., gt=0)
    notas: Optional[str] = Field(None, example="Sin cebolla")

    class Config:
        from_attributes = True


class OrdenItemResponseDTO(BaseModel):
    id: int
    receta_id: int
    cantidad: int
    precio_unitario: int
    notas: Optional[str] = None

    class Config:
        from_attributes = True


class OrdenItemDetalleDTO(BaseModel):
    id: int
    receta_id: int
    cantidad: int
    precio_unitario: int
    estado: str = "pendiente"
    notas: Optional[str] = None
    image: Optional[str] = None

    class Config:
        from_attributes = True


class OrdenDetalleResponseDTO(BaseModel):
    orden_id: int
    mesa_id: int
    mesero_id: int
    num_comensales: int
    estado: str
    hora_apertura: datetime
    notas_generales: Optional[str] = None
    total_bruto: int
    total_neto: int
    items: List[OrdenItemDetalleDTO]

    class Config:
        from_attributes = True


class CrearOrdenResponseDTO(BaseModel):
    orden_id: int
    mesa_id: int
    mesero_id: int
    num_comensales: int
    estado: str
    hora_apertura: datetime
    total_neto: int
    mensaje: str

    class Config:
        from_attributes = True


class ConfirmarOrdenResponseDTO(BaseModel):
    orden_id: int
    estado: str
    hora_confirmacion: datetime
    num_comensales: int
    comanda_ticket: Optional[str] = None
    mensaje: str

    class Config:
        from_attributes = True
