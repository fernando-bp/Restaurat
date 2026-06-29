from __future__ import annotations
from dataclasses import dataclass

@dataclass
class RecetaSub:
    receta_padre_id: int
    receta_base_id: int
    cantidad_g: float
