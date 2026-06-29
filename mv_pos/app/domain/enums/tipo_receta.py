from enum import Enum

class TipoRecetaEnum(str, Enum):
    BASE = 'base'
    FINAL = 'final'
    INSUMO = 'insumo'
