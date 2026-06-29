from enum import Enum

class EstadoOrdenEnum(str, Enum):
    ABIERTA = 'abierta'
    EN_PREPARACION = 'en_preparacion'
    SERVIDA = 'servida'
    CERRADA = 'cerrada'
    PAGADA = 'pagada'
    CANCELADA = 'cancelada'
