from __future__ import annotations
from datetime import datetime
from decimal import Decimal

from app.domain.entities.descuento import Descuento
from app.domain.enums.estado_orden import EstadoOrdenEnum
from app.domain.repositories.orden_repository import OrdenRepository
from app.domain.repositories.descuento_repository import DescuentoRepository


class AplicarDescuentoUC:
    def __init__(
        self,
        orden_repo: OrdenRepository,
        descuento_repo: DescuentoRepository,
    ):
        self.orden_repo = orden_repo
        self.descuento_repo = descuento_repo

    async def ejecutar(
        self,
        orden_id: int,
        porcentaje: Decimal,
        motivo: str,
        autorizado_por: int | None,
        requirio_pin: bool,
        actor_rol: str,
    ) -> Descuento:
        orden = await self.orden_repo.obtener_por_id(orden_id)
        if not orden:
            raise ValueError(f"Orden {orden_id} no encontrada")
        if orden.estado == EstadoOrdenEnum.CANCELADA:
            raise ValueError("No se puede aplicar descuento a una orden cancelada")

        if porcentaje > Decimal('10') and actor_rol != 'administrador':
            raise PermissionError("Descuentos mayores a 10% requieren autorización de administrador")

        base = Decimal(orden.total_bruto) - Decimal(orden.total_descuento)
        if base <= 0:
            raise ValueError("No es posible aplicar más descuentos sobre el total de la orden")

        monto = (base * porcentaje / Decimal('100')).quantize(Decimal('1'))
        if monto <= 0:
            raise ValueError("El monto del descuento debe ser mayor a cero")

        descuento = Descuento(
            id=None,
            orden_id=orden_id,
            porcentaje=porcentaje,
            monto=monto,
            motivo=motivo,
            autorizado_por=autorizado_por,
            requirio_pin=requirio_pin,
            created_at=datetime.utcnow(),
        )
        descuento.validar()

        descuento_guardado = await self.descuento_repo.guardar(descuento)

        orden.total_descuento = int(Decimal(orden.total_descuento) + monto)
        base_final = Decimal(orden.total_bruto) - Decimal(orden.total_descuento)
        orden.total_iva = int((base_final * Decimal('0.19')).quantize(Decimal('1')))
        orden.total_neto = int(base_final + Decimal(orden.total_iva))
        await self.orden_repo.guardar(orden)

        return descuento_guardado
