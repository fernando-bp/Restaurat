from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class InventarioItemDTO(BaseModel):
    id: int
    ingrediente_id: int
    nombre_ingrediente: str
    stock_actual: float
    stock_minimo: float
    stock_maximo: float | None = None
    unidad: str | None = None
    ubicacion: str | None = None
    esta_en_alerta: bool

    class Config:
        from_attributes = True


class AjustarInventarioRequest(BaseModel):
    tipo: Literal["entrada", "perdida"]
    cantidad: float = Field(..., gt=0)
    motivo: str | None = None


class AjustarInventarioResponse(InventarioItemDTO):
    movimiento_id: int
    tipo_movimiento: str


class ActualizarStockRequest(BaseModel):
    stock_actual: float = Field(..., ge=0)
    motivo: str | None = None
