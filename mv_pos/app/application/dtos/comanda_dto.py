from __future__ import annotations
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class ComandaItemDTO(BaseModel):
    receta_nombre: str
    cantidad: int
    observaciones: Optional[str] = None


class ComandaDTO(BaseModel):
    orden_id: int
    mesa_numero: int
    num_comensales: int
    items: List[ComandaItemDTO]
    hora: datetime
    notas_generales: Optional[str] = None

    class Config:
        from_attributes = True
