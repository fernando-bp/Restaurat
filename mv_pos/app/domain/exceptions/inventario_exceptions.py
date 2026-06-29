class StockNegativoException(Exception):
    def __init__(self, message: str = 'La cantidad no puede ser negativa') -> None:
        super().__init__(message)

class StockInsuficienteException(Exception):
    def __init__(self, ingrediente_id: int, disponible: float, requerido: float) -> None:
        super().__init__(f'Stock insuficiente para ingrediente {ingrediente_id}: disponible {disponible}, requerido {requerido}')
        self.ingrediente_id = ingrediente_id
        self.disponible = disponible
        self.requerido = requerido

class StockInsuficienteOrdenException(Exception):
    def __init__(self, detalles: list[dict[str, object]]) -> None:
        super().__init__('Stock insuficiente para confirmar la orden')
        self.detalles = detalles
