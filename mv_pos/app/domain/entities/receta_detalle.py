from __future__ import annotations
from dataclasses import dataclass

@dataclass
class RecetaDetalle:
    ingrediente_id: int
    cantidad: float
    unidad_id: int
    notas: str | None = None
