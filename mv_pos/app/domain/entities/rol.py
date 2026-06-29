from __future__ import annotations
from dataclasses import dataclass

@dataclass
class Rol:
    id: int | None
    nombre: str
    permisos: dict[str, list[str]]
    activo: bool = True

    def tiene_permiso(self, modulo: str, accion: str) -> bool:
        """Retorna True si el rol incluye permiso para la acción en el módulo."""
        acciones = self.permisos.get(modulo, [])
        return accion in acciones
