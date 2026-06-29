from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date, time, datetime

@dataclass
class Reserva:
    id: int | None
    mesa_id: int
    nombre_cliente: str
    telefono_cliente: str | None
    fecha_reserva: date
    hora_reserva: time
    num_personas: int
    notas: str | None
    usuario_id: int
    estado: str = 'activa'
    created_at: datetime = field(default_factory=datetime.utcnow)
