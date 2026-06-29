from __future__ import annotations
from dataclasses import dataclass
from typing import List

from app.domain.enums.tipo_receta import TipoRecetaEnum
from app.domain.entities.receta_detalle import RecetaDetalle
from app.domain.entities.receta_sub import RecetaSub

@dataclass
class Receta:
    id: int | None
    nombre: str
    tipo: TipoRecetaEnum
    numero_receta: str | None
    pax: int
    peso_porcion_g: float | None
    tiempo_prep_min: int | None
    precio_venta: int | None
    categoria_menu: str | None
    activa: bool
    ingredientes: List[RecetaDetalle]
    sub_recetas: List[RecetaSub]
    imagen: bytes | None = None
    imagen_tipo: str | None = None

    def es_tipo_final(self) -> bool:
        return self.tipo == TipoRecetaEnum.FINAL

    def es_tipo_base(self) -> bool:
        return self.tipo == TipoRecetaEnum.BASE

    def validar_precio_venta(self) -> None:
        if self.es_tipo_final() and self.precio_venta is None:
            raise ValueError('Receta final debe tener precio de venta')
