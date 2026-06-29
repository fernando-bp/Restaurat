from enum import Enum


class RolEnum(str, Enum):
    ADMINISTRADOR = 'administrador'
    CHEF = 'chef'
    COCINERO = 'cocinero'
    MESERO = 'mesero'
    CAJERO = 'cajero'
