from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime

from app.domain.entities.rol import Rol

@dataclass
class Usuario:
    id: int | None
    nombre_completo: str
    username: str
    password_hash: str
    rol: Rol
    activo: bool
    sesion_expira: datetime | None

    def tiene_permiso(self, modulo: str, accion: str) -> bool:
        """Verifica si el usuario tiene permiso sobre un módulo y acción."""
        return self.rol.tiene_permiso(modulo, accion)

    def sesion_vigente(self) -> bool:
        """True si la sesión no ha expirado."""
        if self.sesion_expira is None:
            return False
        return datetime.utcnow() < self.sesion_expira
