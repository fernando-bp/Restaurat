from __future__ import annotations
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models.movimientos_inventario import MovimientosInventarioORM


class MovimientoInventarioRepoSQLAlchemy:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def registrar(self, ingrediente_id: int, cantidad: float, stock_resultante: float,
                        precio_unitario_snap: float | None, usuario_id: int, referencia_orden: int | None,
                        motivo: str | None = None, proveedor_id: int | None = None,
                        numero_factura: str | None = None) -> MovimientosInventarioORM:
        movimiento = MovimientosInventarioORM(
            ingrediente_id=ingrediente_id,
            tipo='descuento_venta',
            cantidad=cantidad,
            stock_resultante=stock_resultante,
            precio_unitario_snap=precio_unitario_snap,
            proveedor_id=proveedor_id,
            numero_factura=numero_factura,
            motivo=motivo,
            usuario_id=usuario_id,
            referencia_orden=referencia_orden,
            created_at=datetime.utcnow(),
        )
        self.session.add(movimiento)
        await self.session.commit()
        await self.session.refresh(movimiento)
        return movimiento
