from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime

from app.domain.enums.estado_empleado import EstadoEmpleadoEnum

@dataclass
class Empleado:
    id: int | None
    nombre: str
    apellido: str
    puesto: str
    email: str
    telefono: str | None
    fecha_ingreso: datetime
    estado: EstadoEmpleadoEnum

    def activar(self) -> None:
        self.estado = EstadoEmpleadoEnum.ACTIVO

    def desactivar(self) -> None:
        self.estado = EstadoEmpleadoEnum.INACTIVO
