from __future__ import annotations
from decimal import Decimal
from datetime import datetime
from typing import List, Dict

from app.domain.repositories.orden_repository import OrdenRepository
from app.domain.repositories.descuento_repository import DescuentoRepository
from app.domain.entities.orden import Orden


def to_item_dict(item) -> Dict[str, object]:
    return {
        'id': item.id,
        'receta': item.receta_id,
        'cantidad': item.cantidad,
        'precio_unitario': item.precio_unitario,
        'subtotal': item.subtotal(),
        'notas': item.observaciones,
    }


class ObtenerCuentaDetalladaUC:
    def __init__(
        self,
        orden_repo: OrdenRepository,
        descuento_repo: DescuentoRepository,
    ):
        self.orden_repo = orden_repo
        self.descuento_repo = descuento_repo

    async def ejecutar(self, orden_id: int) -> dict:
        orden = await self.orden_repo.obtener_por_id(orden_id)
        if not orden:
            raise ValueError(f"Orden {orden_id} no encontrada")

        if orden.estado == 'cancelada':
            raise ValueError("No se puede generar la cuenta de una orden cancelada")

        items = [to_item_dict(item) for item in orden.items if item.estado != 'cancelado']
        total_bruto = sum(Decimal(item['subtotal']) for item in items)

        descuentos = []
        total_descuento = Decimal(0)
        descuentos_orden = await self.descuento_repo.listar_por_orden(orden_id)
        for descuento in descuentos_orden:
            descuentos.append({
                'motivo': descuento.motivo,
                'porcentaje': float(descuento.porcentaje),
                'monto': descuento.monto,
            })
            total_descuento += descuento.monto

        base = total_bruto - total_descuento
        if base < 0:
            base = Decimal(0)

        iva = (base * Decimal('0.19')).quantize(Decimal('1'))
        total_neto = (base + iva).quantize(Decimal('1'))

        return {
            'orden_id': orden.id,
            'mesa_id': orden.mesa_id,
            'num_comensales': orden.num_comensales,
            'items': items,
            'total_bruto': total_bruto,
            'descuentos_aplicados': descuentos,
            'total_descuento': total_descuento,
            'iva': iva,
            'total_neto': total_neto,
            'fecha_apertura': orden.hora_apertura,
            'mesa_numero': None,
        }
