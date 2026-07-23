from __future__ import annotations
from decimal import Decimal

from app.domain.enums.estado_orden import EstadoOrdenEnum
from app.domain.enums.tipo_receta import TipoRecetaEnum
from app.domain.entities.orden_item import OrdenItem
from app.domain.exceptions.orden_exceptions import (
    OrdenNoEncontradaException,
    OrdenNoModificableException,
)
from app.domain.repositories.orden_repository import OrdenRepository
from app.domain.repositories.orden_item_repository import OrdenItemRepository


class ModificarOrdenItemUC:
    def __init__(
        self,
        orden_repo: OrdenRepository,
        orden_item_repo: OrdenItemRepository,
        receta_repo,
        inventario_repo,
    ):
        self.orden_repo = orden_repo
        self.orden_item_repo = orden_item_repo
        self.receta_repo = receta_repo
        self.inventario_repo = inventario_repo

    async def execute(self, orden_id: int, orden_item_id: int, cantidad: int, notas: str | None = None) -> OrdenItem:
        orden = await self.orden_repo.obtener_por_id(orden_id)
        if not orden:
            raise OrdenNoEncontradaException(f"Orden ID {orden_id} no existe")

        if orden.estado != EstadoOrdenEnum.ABIERTA:
            raise OrdenNoModificableException(
                f"Orden {orden_id} solo se puede modificar cuando esta abierta"
            )

        item = await self.orden_item_repo.obtener_por_id(orden_item_id)
        if not item or item.orden_id != orden_id:
            raise OrdenNoEncontradaException(f"Ítem {orden_item_id} no corresponde a la orden {orden_id}")

        receta = await self.receta_repo.obtener_por_id(item.receta_id)
        if not receta:
            raise ValueError(f"Receta {item.receta_id} no encontrada")
        if receta.tipo != TipoRecetaEnum.FINAL:
            raise ValueError(f"La receta {item.receta_id} no es un producto final y no puede venderse directamente")

        if cantidad > item.cantidad:
            bom_nueva = await self.receta_repo.explotar_bom(item.receta_id, cantidad)
            bom_vieja = await self.receta_repo.explotar_bom(item.receta_id, item.cantidad)
            for ingrediente_id, cantidad_nueva in bom_nueva.items():
                adicional = cantidad_nueva - bom_vieja.get(ingrediente_id, 0.0)
                if adicional > 0:
                    inventario = await self.inventario_repo.obtener_por_ingrediente(ingrediente_id)
                    if not inventario:
                        raise ValueError(f"Inventario para ingrediente {ingrediente_id} no encontrado")
                    inventario.verificar_suficiente(adicional)

        old_subtotal = item.subtotal()
        item.cantidad = cantidad
        if notas is not None:
            item.observaciones = notas

        updated_item = await self.orden_item_repo.guardar(item)

        nuevo_subtotal = updated_item.subtotal()
        orden.total_bruto = orden.total_bruto - old_subtotal + nuevo_subtotal
        orden.total_iva = int((Decimal(orden.total_bruto) * Decimal('0.08')).quantize(Decimal('1')))
        orden.total_neto = int(Decimal(orden.total_bruto) + Decimal(orden.total_iva))
        await self.orden_repo.guardar(orden)

        return updated_item
