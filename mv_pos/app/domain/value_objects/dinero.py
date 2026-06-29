from __future__ import annotations

class Dinero:
    def __init__(self, cantidad: int) -> None:
        if cantidad < 0:
            raise ValueError('La cantidad en dinero no puede ser negativa')
        self.cantidad = cantidad

    def __int__(self) -> int:
        return self.cantidad

    def __add__(self, other: Dinero) -> Dinero:
        return Dinero(self.cantidad + other.cantidad)

    def __sub__(self, other: Dinero) -> Dinero:
        if self.cantidad < other.cantidad:
            raise ValueError('El resultado del dinero no puede ser negativo')
        return Dinero(self.cantidad - other.cantidad)

    def __str__(self) -> str:
        return str(self.cantidad)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Dinero) and self.cantidad == other.cantidad
