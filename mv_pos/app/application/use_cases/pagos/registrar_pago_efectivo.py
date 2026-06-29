"""
RF-28: Procesar pagos en efectivo con cálculo de cambio
"""
from decimal import Decimal
from datetime import datetime

from app.domain.entities.pago import Pago
from app.domain.enums.forma_pago import FormaPagoEnum
from app.domain.enums.estado_orden import EstadoOrdenEnum
from app.domain.repositories.orden_repository import OrdenRepository
from app.domain.repositories.pago_repository import PagoRepository
from app.domain.repositories.mesa_repository import MesaRepository


class RegistrarPagoEfectivoUseCase:
    """Registra pagos en efectivo y calcula cambio (RF-28)"""

    def __init__(
        self,
        orden_repo: OrdenRepository,
        pago_repo: PagoRepository,
        mesa_repo: MesaRepository,
    ):
        self.orden_repo = orden_repo
        self.pago_repo = pago_repo
        self.mesa_repo = mesa_repo

    async def ejecutar(
        self,
        orden_id: int,
        monto_adeudado: Decimal,
        monto_recibido: Decimal,
        cajero_id: int,
    ) -> dict:
        if monto_recibido < monto_adeudado:
            raise ValueError(
                f"Dinero insuficiente. Adeudado: {monto_adeudado}, "
                f"Recibido: {monto_recibido}"
            )

        orden = await self.orden_repo.obtener_por_id(orden_id)
        if not orden:
            raise ValueError(f"Orden {orden_id} no encontrada")
        if orden.estado == EstadoOrdenEnum.CANCELADA:
            raise ValueError("No se puede pagar una orden cancelada")

        pago = Pago(
            id=None,
            orden_id=orden_id,
            forma_pago=FormaPagoEnum.EFECTIVO,
            monto=monto_adeudado,
            monto_recibido=monto_recibido,
            cajero_id=cajero_id,
            created_at=datetime.utcnow(),
        )
        pago.validar_efectivo()
        pago.cambio_entregado = pago.calcular_cambio()

        pago_guardado = await self.pago_repo.guardar(pago)

        orden_pagado = await self.pago_repo.listar_por_orden(orden_id)
        total_pagado = sum(p.monto for p in orden_pagado)
        if total_pagado >= Decimal(orden.total_neto):
            orden.estado = EstadoOrdenEnum.PAGADA
            orden.hora_cierre = datetime.utcnow()
            await self.orden_repo.guardar(orden)

            mesa = await self.mesa_repo.obtener_por_id(orden.mesa_id)
            if mesa:
                mesa.estado = 'libre'
                await self.mesa_repo.guardar(mesa)

        return {
            'pago_id': pago_guardado.id,
            'monto_pagado': pago_guardado.monto,
            'monto_recibido': pago_guardado.monto_recibido,
            'cambio': pago_guardado.cambio_entregado,
            'exito': True,
        }
