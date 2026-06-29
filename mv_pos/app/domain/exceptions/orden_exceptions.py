class TransicionEstadoInvalidaException(Exception):
    pass


class OrdenNoEncontradaException(Exception):
    pass


class OrdenNoConfirmableException(Exception):
    pass


class OrdenNoModificableException(Exception):
    pass


class TransferenciaMesaException(Exception):
    """Excepción para operaciones de transferencia de mesas"""
    pass


class UnionMesasException(Exception):
    """Excepción para operaciones de unión de mesas"""
    pass

