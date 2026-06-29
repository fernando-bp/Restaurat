from __future__ import annotations
from typing import List, Optional

from pydantic import BaseModel


class RecetaListItemDTO(BaseModel):
    id: int
    nombre: str
    precio_venta: Optional[int] = None
    categoria_menu: Optional[str] = None
    activa: bool
    imagen_base64: Optional[str] = None

    class Config:
        from_attributes = True


class RecetaIngredienteDTO(BaseModel):
    ingrediente_id: int
    nombre: Optional[str] = None
    cantidad: float
    unidad_id: int
    unidad: Optional[str] = None
    costo_unitario: Optional[float] = None
    costo_total: Optional[float] = None
    notas: Optional[str] = None


class RecetaSubDetalleDTO(BaseModel):
    receta_base_id: int
    nombre: Optional[str] = None
    cantidad_g: float
    ingredientes: List[RecetaIngredienteDTO] = []
    sub_recetas: List["RecetaSubDetalleDTO"] = []


class RecetaDetalleDTO(BaseModel):
    id: int
    nombre: str
    tipo: str
    numero_receta: Optional[str] = None
    pax: int
    peso_porcion_g: Optional[float] = None
    tiempo_prep_min: Optional[int] = None
    precio_venta: Optional[int] = None
    categoria_menu: Optional[str] = None
    activa: bool
    imagen_base64: Optional[str] = None
    ingredientes: List[RecetaIngredienteDTO] = []
    sub_recetas: List[RecetaSubDetalleDTO] = []


class RecetaUpdateDTO(BaseModel):
    nombre: str
    tipo: str = "final"
    numero_receta: Optional[str] = None
    pax: int = 1
    peso_porcion_g: Optional[float] = None
    tiempo_prep_min: Optional[int] = None
    precio_venta: Optional[int] = None
    categoria_menu: Optional[str] = None
    activa: bool = True
    imagen_base64: Optional[str] = None
    ingredientes: List[RecetaIngredienteDTO] = []
    sub_recetas: List[RecetaSubDetalleDTO] = []
