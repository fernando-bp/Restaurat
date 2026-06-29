from enum import Enum

class EstadoProduccionEnum(str, Enum):
    PENDIENTE = 'pendiente'
    EN_PREPARACION = 'en_preparacion'
    FINALIZADO = 'finalizado'
