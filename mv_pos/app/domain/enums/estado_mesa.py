from enum import Enum

class EstadoMesaEnum(str, Enum):
    LIBRE = 'libre'
    OCUPADA = 'ocupada'
    RESERVADA = 'reservada'
    EN_ESPERA_CUENTA = 'en_espera_cuenta'
    LIMPIANDO = 'limpiando'
