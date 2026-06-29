from __future__ import annotations

class Money:
    def __init__(self, amount: int) -> None:
        if amount < 0:
            raise ValueError('El monto no puede ser negativo')
        self.amount = amount

    def __int__(self) -> int:
        return self.amount

    def __add__(self, other: Money) -> Money:
        return Money(self.amount + other.amount)

    def __sub__(self, other: Money) -> Money:
        if self.amount < other.amount:
            raise ValueError('El resultado del dinero no puede ser negativo')
        return Money(self.amount - other.amount)

    def __str__(self) -> str:
        return str(self.amount)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Money) and self.amount == other.amount
