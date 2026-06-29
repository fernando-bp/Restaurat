from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime

from app.domain.enums.estado_produccion import EstadoProduccionEnum

@dataclass
class Produccion:
    id: int | None
    receta_id: int
    cantidad: float
    estado: EstadoProduccionEnum
    fecha_creacion: datetime
    fecha_finalizacion: datetime | None = None

    def finalizar(self) -> None:
        if self.estado == EstadoProduccionEnum.FINALIZADO:
            raise ValueError('Producción ya finalizada')
        self.estado = EstadoProduccionEnum.FINALIZADO
        self.fecha_finalizacion = datetime.utcnow()
