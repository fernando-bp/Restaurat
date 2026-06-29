class MesaNoEncontradaException(Exception):
    """Excepción: Mesa no existe"""
    pass


class MesaNoDisponibleException(Exception):
    """Excepción: Mesa no está disponible para abrir"""
    pass


class CapacidadMesaExcedidaException(Exception):
    """Excepción: Número de comensales excede capacidad de mesa"""
    pass


class ReservaMesaException(Exception):
    """Excepción: Error al crear o gestionar reservas de mesa"""
    pass
