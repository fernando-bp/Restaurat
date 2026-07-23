from __future__ import annotations
from decimal import Decimal

from app.domain.enums.estado_orden import EstadoOrdenEnum
from app.domain.exceptions.orden_exceptions import (
    OrdenNoEncontradaException,
    OrdenNoModificableException,
)
from app.domain.repositories.orden_repository import OrdenRepository
from app.domain.repositories.orden_item_repository import OrdenItemRepository


class EliminarOrdenItemUC:
    def __init__(self, orden_repo: OrdenRepository, orden_item_repo: OrdenItemRepository):
        self.orden_repo = orden_repo
        self.orden_item_repo = orden_item_repo

    async def execute(self, orden_id: int, orden_item_id: int) -> None:
        orden = await self.orden_repo.obtener_por_id(orden_id)
        if not orden:
            raise OrdenNoEncontradaException(f"Orden ID {orden_id} no existe")

        estados_modificables = {EstadoOrdenEnum.ABIERTA, EstadoOrdenEnum.EN_PREPARACION}
        if orden.estado not in estados_modificables:
            raise OrdenNoModificableException(
                f"Orden {orden_id} solo se puede modificar cuando está abierta o en preparación"
            )

        item = await self.orden_item_repo.obtener_por_id(orden_item_id)
        if not item or item.orden_id != orden_id:
            raise OrdenNoEncontradaException(f"Ítem {orden_item_id} no corresponde a la orden {orden_id}")

        subtotal = item.subtotal()
        await self.orden_item_repo.eliminar(orden_item_id)

        orden.total_bruto = max(0, orden.total_bruto - subtotal)
        orden.total_iva = int((Decimal(orden.total_bruto) * Decimal('0.08')).quantize(Decimal('1')))
        orden.total_neto = int(Decimal(orden.total_bruto) + Decimal(orden.total_iva))
        await self.orden_repo.guardar(orden)
