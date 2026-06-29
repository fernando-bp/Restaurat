from __future__ import annotations
from dataclasses import dataclass

from app.domain.exceptions.inventario_exceptions import StockNegativoException, StockInsuficienteException

@dataclass
class Inventario:
    id: int | None
    ingrediente_id: int
    stock_actual: float
    stock_minimo: float
    stock_maximo: float | None
    ubicacion: str | None

    def esta_en_alerta(self) -> bool:
        return self.stock_actual <= self.stock_minimo

    def verificar_suficiente(self, cantidad: float) -> None:
        if cantidad < 0:
            raise StockNegativoException('La cantidad a verificar no puede ser negativa')
        if self.stock_actual < cantidad:
            raise StockInsuficienteException(ingrediente_id=self.ingrediente_id, disponible=self.stock_actual, requerido=cantidad)

    def descontar(self, cantidad: float) -> None:
        if cantidad < 0:
            raise StockNegativoException('La cantidad a descontar no puede ser negativa')
        if self.stock_actual - cantidad < 0:
            raise StockInsuficienteException(ingrediente_id=self.ingrediente_id, disponible=self.stock_actual, requerido=cantidad)
        self.stock_actual -= cantidad
