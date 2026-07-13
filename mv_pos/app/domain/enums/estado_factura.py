from enum import Enum


class EstadoFacturaEnum(str, Enum):
    BORRADOR = "borrador"
    PENDIENTE = "pendiente"
    PROCESSING = "processing"
    VALIDATED = "validated"
    ACEPTADA = "aceptada"
    RECHAZADA = "rechazada"
    REJECTED = "rejected"
    ANULADA = "anulada"
